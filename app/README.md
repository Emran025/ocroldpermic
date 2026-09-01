# Archival Vision Lab

> A generic, offline-first Flutter OCR runtime for traceable manuscript transcription.

**Archival Vision Lab** turns OCR model packages into a reviewable research workflow. It accepts a self-describing OCR package, runs compatible ONNX inference on the device, overlays glyph detections on the source image, reconstructs reading order, and exports both the raw model output and the researcher's corrected transcription.

The application is intentionally **not coupled to one language or writing system**. A package supplies its own alphabet, Unicode mapping, script metadata, preprocessing contract, model artifact, output decoder, and reading direction. The runtime supplies the secure installation, inference, inspection, correction, and export experience.

## Project description

Archival Vision Lab is designed for researchers working with historical manuscripts and other specialist writing systems. It treats machine-generated transcription as evidence that must remain visible and reviewable—not as an authoritative reading. Every detected glyph can be inspected with its bounding box, confidence score, Unicode mapping, and model alternatives. Every exported result records the exact package, model, alphabet, thresholds, image dimensions, and inference time used to produce it.

The project combines a responsive Material 3 interface with a Clean Architecture core. It can operate offline after a model package has been installed, while still supporting secure package updates and validated remote image inputs when connectivity is available. Its localization approach follows Flutter's generated internationalization model [1], its inference boundary is built around ONNX Runtime [2], and its remote gateway is isolated behind a Dio-backed consumer [3].

## Core capabilities

| Capability | Implementation |
| --- | --- |
| Generic script support | Self-describing OCR package manifest with dynamic class-to-Unicode mapping |
| Local inference | ONNX Runtime adapter with model-declared preprocessing and YOLO v8 decoding |
| Research review | Source-image overlay, line reconstruction, confidence, alternatives, and glyph inspection |
| Safe model lifecycle | SHA-256 verification, size limits, safe archive extraction, candidate staging, and atomic activation |
| Input sources | Gallery, camera, file picker, local `.ocrpkg`, HTTPS package URL, HTTPS manifest URL, and validated image URL |
| Reproducibility | TXT, research JSON, and glyph-level CSV export with package and runtime metadata |
| Internationalization | Generated Arabic and English localization catalogs with locale-aware Material widgets |
| Theming | Centralized light, dark, and reading themes with the Archival Vision Lab olive/paper palette |

## User workflow

1. **Install a package.** Import a local `.ocrpkg` archive or download a package/manifest from an HTTP(S) source.
2. **Select the source.** Choose a manuscript image from the gallery, camera, file picker, or a validated remote URL.
3. **Run locally.** Execute ONNX inference on the device using the active package's declared contract.
4. **Inspect evidence.** Review bounding boxes, class labels, Unicode values, confidence, alternatives, and reconstructed lines.
5. **Correct carefully.** Edit the transcription while preserving the raw model output separately.
6. **Export reproducibly.** Save plain text, structured research JSON, or glyph-level CSV for further analysis.

## Architecture

The codebase follows a dependency direction that keeps the domain independent from Flutter widgets, Dio, ONNX Runtime, and filesystem details.

| Layer | Responsibility |
| --- | --- |
| `lib/domain` | Package entities, OCR results, reading order, ports, and use cases |
| `lib/data` | Manifest parsing and compatibility validation |
| `lib/infrastructure` | HTTP catalog, package storage, archive safety, image loading, ONNX inference, and exports |
| `lib/core/api` | `ApiConsumer` contract, centralized `DioConsumer`, and network error translation |
| `lib/core/themes` | Light, dark, and reading theme construction |
| `lib/core/constants` | Product color tokens |
| `lib/config/localization` | ARB sources, generated localization API, delegates, locales, and message tokens |
| `lib/presentation` | Responsive workspace UI and explicit OCR workflow state |

The presentation and domain layers never need to know how a manifest was hosted. `DioConsumer` centralizes ordinary API requests, while the storage and image adapters use streaming-oriented Dio operations where file transfer semantics are required.

## Localization and language structure

All application-visible copy is maintained in ARB catalogs:

```text
lib/config/localization/
├── l10n_config.dart
├── l10n_context.dart
├── workspace_messages.dart
└── l10n/
    ├── app_en.arb
    ├── app_ar.arb
    ├── app_localizations.dart
    ├── app_localizations_en.dart
    └── app_localizations_ar.dart
```

English is the template locale and Arabic is supported as a first-class locale. The app registers Flutter's Material, Widgets, Cupertino, and generated application delegates [4]. To add a new language, add an `app_<locale>.arb` catalog, update `L10nConfig.supportedLocales`, and regenerate the typed API:

```bash
flutter gen-l10n
```

Do not add user-facing text directly to widgets or controllers. Add a message key to both catalogs, regenerate, and access it through `context.l10n` or `WorkspaceMessages`.

## OCR package contract

A package is a ZIP-compatible `.ocrpkg` archive containing a root `manifest.json`, an ONNX model artifact, and an alphabet artifact. The manifest declares model format, input layout, normalization, output tensor layout, box format, coordinates, reading direction, runtime compatibility, file sizes, and SHA-256 digests.

Read the complete [OCR Package Contract v1](docs/OCR_PACKAGE_CONTRACT.md) before producing or distributing a package. The runtime rejects incompatible, malformed, tampered, oversized, or unsafe packages before activation.

## Theme system

The theme structure follows a centralized `AppThemes`/`AppColors` pattern. Three theme types are available:

- **Light:** warm paper surface with olive actions and graphite text.
- **Dark:** graphite and ink surfaces with accessible paper text.
- **Reading:** a focused manuscript-reading surface using the warm reading-paper palette.

The palette is based on the deployed OCR lab visual language rather than the teaching application's colors. Widgets consume `ColorScheme` and theme tokens instead of embedding product colors.

## Development

### Requirements

- Flutter stable with Dart 3.4 or newer.
- A platform toolchain for the target device.
- A compatible ONNX Runtime platform configuration for device builds.

### Commands

```bash
flutter pub get
flutter gen-l10n
flutter analyze
flutter test
flutter run
```

The test suite covers manifest parsing, runtime compatibility, alphabet mapping, reading order, YOLO decoding and suppression, mocked OCR execution, localization generation, and the primary workspace shell.

## Engineering principles

The runtime does not fabricate OCR output when no compatible package is installed. It keeps raw output separate from corrected text, verifies artifacts before activation, preserves the active package during failed updates, and records enough metadata to reproduce an exported result. These constraints are deliberate: an OCR suggestion should be inspectable, reversible, and attributable.

## References

[1]: https://docs.flutter.dev/ui/accessibility-and-internationalization/internationalization "Flutter internationalization documentation"

[2]: https://onnxruntime.ai/docs/get-started/with-javascript.html "ONNX Runtime documentation"

[3]: https://pub.dev/packages/dio "Dio package documentation"

[4]: https://pub.dev/packages/flutter_localizations "Flutter localizations package"
