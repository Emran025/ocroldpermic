# OCR Runtime for Flutter

A clean, offline-first **OCR inference runtime** for self-describing OCR model packages. The repository name reflects its origin, but the application is not coupled to Old Permic or any other alphabet. Language and script knowledge come from the installed package's manifest and alphabet mapping.

## Product workflow

1. Install an OCR package from a local `.ocrpkg` archive, HTTPS package URL, or HTTPS manifest URL.
2. Select an image from the gallery or file picker, capture it with the camera, or use a validated remote image URL.
3. Run local ONNX inference.
4. Review detections, confidence, Unicode mapping, and model-supplied alternatives.
5. Correct the editable transcription without overwriting the raw model result.
6. Export TXT, research JSON, or glyph-level CSV with reproducibility metadata.

## Architecture

The app preserves a Clean Architecture boundary:

| Layer | Responsibility |
| --- | --- |
| `domain/entities` | Package contract, alphabet, detections, results, reading order |
| `domain/repositories` | Model catalog, model repository, image/inference ports |
| `domain/usecases` | OCR execution and text reconstruction |
| `data/models` | Versioned manifest parsing and compatibility validation |
| `infrastructure` | HTTP catalog, package storage, secure archive import, ONNX inference, exports |
| `presentation` | Responsive model/image/run/review workspace and explicit workflow state |

The `OnnxYoloInferenceEngine` is the only component coupled to ONNX Runtime. It can be complemented by future runtime adapters without changing results, model management, or presentation code.

## Safety and offline behavior

The model repository verifies SHA-256 digests and declared file sizes, stages downloads in candidate directories, and only switches the active model pointer after validation. Imported archives reject unsafe paths and enforce compressed/extracted size limits. A failed install or update leaves the existing active model untouched.

Once installed, an OCR package and local inference work without an internet connection. Network access is only needed for remote package/image sources and update checks.

## OCR package contract

See [OCR Package Contract v1](docs/OCR_PACKAGE_CONTRACT.md) for the full versioned manifest, package layout, YOLO output requirements, integrity expectations, and reproducible export contents.

## Local development

```bash
flutter pub get
flutter analyze
flutter test
flutter run
```

The current inference adapter expects YOLO v8 ONNX models and validates the package-declared input/output contract before use. It does not fabricate OCR results when no compatible model has been installed.
