import '../entities/ocr_result.dart';
import '../entities/release_manifest.dart';
import '../repositories/ocr_ports.dart';

class RunOcr {
  const RunOcr(this._inference, {this.readingOrder = const ReadingOrder()});

  final OcrInference _inference;
  final ReadingOrder readingOrder;

  Future<OcrResult> call({
    required String imagePath,
    required InstalledModel model,
    required OcrRunConfiguration configuration,
  }) async {
    final output = await _inference.infer(imagePath, model, configuration);
    return OcrResult(
      orderedText: readingOrder.order(output.detections,
          direction: model.manifest.readingDirection),
      model: model,
      inputPath: imagePath,
      createdAt: DateTime.now().toUtc(),
      inferenceTime: output.elapsed,
      configuration: configuration,
      imageWidth: output.imageWidth,
      imageHeight: output.imageHeight,
    );
  }
}
