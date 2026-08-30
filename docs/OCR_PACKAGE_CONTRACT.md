# OCR Package Contract v1

The application is a **generic OCR runtime**. A package—not Flutter source code—defines the language, writing system, class-to-Unicode mapping, model artifact, and model-specific preprocessing contract. A compatible package can therefore introduce a new historical or contemporary writing system without rebuilding the application.

## Package layout

A locally importable package uses a ZIP-compatible `.ocrpkg` archive. Its paths are relative to the archive root and must not contain `..`, absolute paths, or backslashes.

```text
my-script-1.0.0.ocrpkg
├── manifest.json
├── model/
│   └── detector.onnx
└── alphabet/
    └── classes.json
```

Remote distribution uses the same `manifest.json` at an HTTPS URL. Artifact paths may be relative to that URL or fully qualified HTTPS URLs. The domain layer has no dependency on GitHub; GitHub Releases are simply one possible HTTPS host.

## Manifest schema

The app accepts a `schema_version` of `1`. Every model artifact must declare a byte size and lowercase SHA-256 digest. The inline alphabet makes the package self-describing before installation. The separate alphabet artifact is optional for legacy packages, but required for new release pipelines because it makes the full class map independently auditable.

```json
{
  "schema_version": 1,
  "package_id": "historical-greek-glyphs",
  "version": "2.1.0",
  "model_version": "2.1.0-yolo8n",
  "language": "Historical Greek",
  "script": "Greek",
  "reading_direction": "ltr",
  "alphabet_version": "2026.08",
  "minimum_runtime_version": "1.0.0",
  "created_at": "2026-08-30T00:00:00Z",
  "model_format": "onnx",
  "model": {
    "id": "detector",
    "path": "model/detector.onnx",
    "bytes": 18432192,
    "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "media_type": "application/onnx"
  },
  "alphabet": {
    "version": "2026.08",
    "artifact": {
      "id": "alphabet",
      "path": "alphabet/classes.json",
      "bytes": 12640,
      "sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
    },
    "classes": [
      {
        "id": 0,
        "unicode": "U+0391",
        "character": "Α",
        "name": "GREEK CAPITAL LETTER ALPHA",
        "display": "Α"
      }
    ]
  },
  "input": {
    "width": 640,
    "height": 640,
    "layout": "nchw",
    "channels": 3,
    "normalization": "zero_to_one",
    "letterbox": true,
    "pad_color": 114
  },
  "output": {
    "decoder": "yolo_v8",
    "layout": "channels_first",
    "box_format": "xywh",
    "coordinates": "pixels",
    "has_objectness": false
  }
}
```

## Required validation

Before a package can become active, the runtime validates the schema version, model format, runtime version, input dimensions, non-empty alphabet, unique non-negative class IDs, Unicode scalar values, and the model artifact size and SHA-256 digest. Imported archives are capped at 1 GB compressed and extracted, reject path traversal, and only write into an isolated candidate directory.

An installation is activated only after all validations have completed. The runtime writes a new active-package pointer atomically, so a failed download, checksum mismatch, malformed package, or unsuccessful update leaves the current active package untouched.

## YOLO v8 output contract

The current runtime implements YOLO v8 class-detection tensors. `channels_first` indicates `[1, 4 + class_count, predictions]`; `predictions_first` indicates `[1, predictions, 4 + class_count]`. Four box values are either `xywh` or `xyxy`, with pixel or normalized coordinates as declared by `output`. Class score positions map by **class ID** through the package alphabet, never through script-specific source code.

Alternative predictions shown by the app are the top class scores emitted by the model. They are not generated or inferred by the user interface.

## Reproducible results

Research JSON exports retain raw and corrected transcriptions, package/model/alphabet versions, timestamp, inference time, configured confidence and IoU thresholds, glyph-level Unicode values, confidence, alternatives, and original-image bounding boxes. This makes a transcription traceable to the precise OCR package that produced it.
