import 'dart:io';

import 'package:onnxruntime/onnxruntime.dart';

import '../../domain/entities/ocr_result.dart';
import '../../domain/entities/release_manifest.dart';
import '../../domain/repositories/ocr_ports.dart';
import 'image_preprocessor.dart';
import 'yolo_postprocessor.dart';

/// On-device ONNX Runtime adapter. Only this infrastructure class knows about
/// ORT sessions; the rest of the application deals in OCR domain objects.
class OnnxYoloInferenceEngine implements OcrInference {
  OnnxYoloInferenceEngine({
    this.preprocessor = const ImagePreprocessor(),
    this.postProcessor = const YoloPostProcessor(),
  });

  final ImagePreprocessor preprocessor;
  final YoloPostProcessor postProcessor;
  static bool _environmentInitialized = false;

  @override
  Future<InferenceOutput> infer(
    String imagePath,
    InstalledModel model,
    OcrRunConfiguration configuration,
  ) async {
    if (model.manifest.modelFormat != ModelFormat.onnx) {
      throw UnsupportedError(
          'The active package requires ${model.manifest.modelFormat.name}, but this runtime only has ONNX support.');
    }
    final modelFile = File(model.modelPath);
    final imageFile = File(imagePath);
    if (!await modelFile.exists()) {
      throw const FileSystemException('The active model file is missing.');
    }
    if (!await imageFile.exists()) {
      throw const FileSystemException('The selected image is missing.');
    }
    if (!_environmentInitialized) {
      OrtEnv.instance.init();
      _environmentInitialized = true;
    }

    final prepared = preprocessor.prepare(
        await imageFile.readAsBytes(), model.manifest.input);
    final sessionOptions = OrtSessionOptions();
    final session =
        OrtSession.fromBuffer(await modelFile.readAsBytes(), sessionOptions);
    final input = OrtValueTensor.createTensorWithDataList(
        prepared.tensor, prepared.shape);
    final runOptions = OrtRunOptions();
    final stopwatch = Stopwatch()..start();
    List<OrtValue?>? outputs;
    try {
      outputs =
          await session.runAsync(runOptions, {session.inputNames.first: input});
      stopwatch.stop();
      if (outputs == null || outputs.isEmpty || outputs.first == null) {
        throw const FormatException('The model returned no output tensor.');
      }
      final values = List<num>.from(outputs.first!.value as List);
      final detections = postProcessor.decode(
        values: values,
        manifest: model.manifest,
        image: prepared,
        configuration: configuration,
      );
      return InferenceOutput(
        detections: detections,
        elapsed: stopwatch.elapsed,
        imageWidth: prepared.originalWidth,
        imageHeight: prepared.originalHeight,
      );
    } finally {
      for (final output in outputs ?? const <OrtValue?>[]) {
        output?.release();
      }
      input.release();
      runOptions.release();
      session.release();
      sessionOptions.release();
    }
  }
}
