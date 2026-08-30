import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';

import '../../domain/entities/ocr_result.dart';

enum OcrExportFormat { text, json, csv }

class OcrResultExporter {
  Future<File> export(OcrResult result, OcrExportFormat format) async {
    final documents = await getApplicationDocumentsDirectory();
    final folder = Directory('${documents.path}/ocr_exports');
    await folder.create(recursive: true);
    final stamp = result.createdAt.toIso8601String().replaceAll(':', '-');
    final file = File(
        '${folder.path}/${_safeName(result.model.manifest.packageId)}-$stamp.${format.name == 'text' ? 'txt' : format.name}');
    final contents = switch (format) {
      OcrExportFormat.text => result.resolvedText,
      OcrExportFormat.json =>
        const JsonEncoder.withIndent('  ').convert(_json(result)),
      OcrExportFormat.csv => _csv(result),
    };
    await file.writeAsString(contents, flush: true);
    return file;
  }

  Map<String, dynamic> _json(OcrResult result) => {
        'transcription': {
          'raw': result.rawText,
          'edited': result.editedText,
          'resolved': result.resolvedText,
        },
        'reproducibility': {
          'package_id': result.model.manifest.packageId,
          'package_version': result.model.manifest.version,
          'model_version': result.model.manifest.modelVersion,
          'alphabet_version': result.model.manifest.alphabetVersion,
          'script': result.model.manifest.script,
          'runtime_version': '1.0.0',
          'created_at': result.createdAt.toIso8601String(),
          'inference_ms': result.inferenceTime.inMilliseconds,
          'confidence_threshold': result.configuration.confidenceThreshold,
          'iou_threshold': result.configuration.iouThreshold,
          'input_path': result.inputPath,
        },
        'lines': result.orderedText.lines
            .map((line) => {
                  'text': line.text,
                  'baseline': line.baseline,
                  'glyphs': line.detections.map(_glyphJson).toList(),
                })
            .toList(),
      };

  Map<String, dynamic> _glyphJson(GlyphDetection detection) => {
        'class_id': detection.glyph.id,
        'unicode': detection.glyph.unicode,
        'character': detection.glyph.label,
        'name': detection.glyph.name,
        'confidence': detection.confidence,
        'bounding_box': {
          'left': detection.left,
          'top': detection.top,
          'right': detection.right,
          'bottom': detection.bottom,
        },
        'alternatives': detection.alternatives
            .map((item) => {
                  'class_id': item.glyph.id,
                  'unicode': item.glyph.unicode,
                  'character': item.glyph.label,
                  'confidence': item.confidence
                })
            .toList(),
      };

  String _csv(OcrResult result) {
    final rows = <List<Object?>>[
      [
        'line',
        'order',
        'class_id',
        'unicode',
        'character',
        'confidence',
        'left',
        'top',
        'right',
        'bottom'
      ],
    ];
    for (var lineIndex = 0;
        lineIndex < result.orderedText.lines.length;
        lineIndex++) {
      final line = result.orderedText.lines[lineIndex];
      for (var order = 0; order < line.detections.length; order++) {
        final glyph = line.detections[order];
        rows.add([
          lineIndex + 1,
          order + 1,
          glyph.glyph.id,
          glyph.glyph.unicode,
          glyph.glyph.label,
          glyph.confidence,
          glyph.left,
          glyph.top,
          glyph.right,
          glyph.bottom
        ]);
      }
    }
    return rows.map((row) => row.map(_csvValue).join(',')).join('\n');
  }

  String _csvValue(Object? value) =>
      '"${(value?.toString() ?? '').replaceAll('"', '""')}"';
  String _safeName(String value) =>
      value.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
}
