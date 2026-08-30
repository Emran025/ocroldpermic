import 'dart:math' as math;
import 'dart:typed_data';

import 'package:image/image.dart' as img;

import '../../domain/entities/release_manifest.dart';

class PreprocessedImage {
  const PreprocessedImage({
    required this.tensor,
    required this.shape,
    required this.originalWidth,
    required this.originalHeight,
    required this.scale,
    required this.padX,
    required this.padY,
  });

  final Float32List tensor;
  final List<int> shape;
  final int originalWidth;
  final int originalHeight;
  final double scale;
  final double padX;
  final double padY;
}

/// Decodes once at model resolution and applies model-declared normalization.
class ImagePreprocessor {
  const ImagePreprocessor();

  PreprocessedImage prepare(Uint8List encodedImage, InputSpec spec) {
    final decoded = img.decodeImage(encodedImage);
    if (decoded == null) {
      throw const FormatException('The image could not be decoded.');
    }
    final source = img.bakeOrientation(decoded);
    final scale = spec.letterbox
        ? math.min(spec.width / source.width, spec.height / source.height)
        : math.max(spec.width / source.width, spec.height / source.height);
    final scaledWidth = math.max(1, (source.width * scale).round());
    final scaledHeight = math.max(1, (source.height * scale).round());
    final resized = img.copyResize(source,
        width: scaledWidth,
        height: scaledHeight,
        interpolation: img.Interpolation.linear);
    final canvas =
        img.Image(width: spec.width, height: spec.height, numChannels: 3);
    for (var y = 0; y < canvas.height; y++) {
      for (var x = 0; x < canvas.width; x++) {
        canvas.setPixelRgb(x, y, spec.padColor, spec.padColor, spec.padColor);
      }
    }
    final padX = (spec.width - scaledWidth) / 2;
    final padY = (spec.height - scaledHeight) / 2;
    img.compositeImage(canvas, resized, dstX: padX.round(), dstY: padY.round());

    final tensor = Float32List(spec.width * spec.height * spec.channels);
    var index = 0;
    double convert(num value) => switch (spec.normalization) {
          'minus_one_to_one' => (value / 127.5) - 1,
          'none' => value.toDouble(),
          _ => value / 255,
        };
    if (spec.layout == TensorLayout.nchw) {
      for (var channel = 0; channel < spec.channels; channel++) {
        for (var y = 0; y < spec.height; y++) {
          for (var x = 0; x < spec.width; x++) {
            final pixel = canvas.getPixel(x, y);
            final value = switch (channel) {
              0 => pixel.r,
              1 => pixel.g,
              2 => pixel.b,
              _ => pixel.a,
            };
            tensor[index++] = convert(value);
          }
        }
      }
    } else {
      for (var y = 0; y < spec.height; y++) {
        for (var x = 0; x < spec.width; x++) {
          final pixel = canvas.getPixel(x, y);
          final channels = [pixel.r, pixel.g, pixel.b, pixel.a];
          for (var channel = 0; channel < spec.channels; channel++) {
            tensor[index++] = convert(channels[channel]);
          }
        }
      }
    }
    return PreprocessedImage(
      tensor: tensor,
      shape: spec.layout == TensorLayout.nchw
          ? [1, spec.channels, spec.height, spec.width]
          : [1, spec.height, spec.width, spec.channels],
      originalWidth: source.width,
      originalHeight: source.height,
      scale: scale,
      padX: padX,
      padY: padY,
    );
  }
}
