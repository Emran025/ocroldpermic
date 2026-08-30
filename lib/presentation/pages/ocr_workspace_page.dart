import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../domain/entities/ocr_result.dart';
import '../../domain/entities/release_manifest.dart';
import '../../infrastructure/storage/ocr_result_exporter.dart';
import '../state/ocr_workspace_controller.dart';

class OcrWorkspacePage extends StatefulWidget {
  const OcrWorkspacePage(
      {super.key, required this.workspace, required this.onToggleTheme});

  final OcrWorkspaceController workspace;
  final VoidCallback onToggleTheme;

  @override
  State<OcrWorkspacePage> createState() => _OcrWorkspacePageState();
}

class _OcrWorkspacePageState extends State<OcrWorkspacePage> {
  final _picker = ImagePicker();
  final _textController = TextEditingController();
  OcrResult? _lastResult;
  GlyphDetection? _selectedGlyph;
  bool _showBoxes = true;
  bool _showLabels = true;
  bool _showConfidence = false;
  bool _showUnicode = false;

  @override
  void initState() {
    super.initState();
    widget.workspace.initialize();
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  Future<void> _chooseImage(ImageSource source) async {
    final picked = await _picker.pickImage(
        source: source, imageQuality: 95, maxWidth: 4096, maxHeight: 4096);
    if (picked != null) widget.workspace.setImage(picked.path);
  }

  Future<void> _choosePackage() async {
    final file = await FilePicker.platform.pickFiles(
        type: FileType.custom, allowedExtensions: const ['ocrpkg', 'zip']);
    final path = file?.files.single.path;
    if (path != null) await widget.workspace.importPackage(path);
  }

  Future<void> _chooseImageFile() async {
    final file = await FilePicker.platform.pickFiles(type: FileType.image);
    final path = file?.files.single.path;
    if (path != null) widget.workspace.setImage(path);
  }

  Future<void> _addRemotePackage() async {
    final controller = TextEditingController();
    final source = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add OCR package'),
        content: TextField(
          controller: controller,
          autofocus: true,
          keyboardType: TextInputType.url,
          decoration: const InputDecoration(
            labelText: 'Package manifest URL',
            hintText: 'https://example.org/manifest.json',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(context, controller.text),
              child: const Text('Verify & install')),
        ],
      ),
    );
    controller.dispose();
    if (source != null && source.trim().isNotEmpty) {
      await widget.workspace.installRemoteManifest(source);
    }
  }

  Future<void> _addRemotePackageArchive() async {
    final controller = TextEditingController();
    final source = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Install remote OCR package'),
        content: TextField(
          controller: controller,
          autofocus: true,
          keyboardType: TextInputType.url,
          decoration: const InputDecoration(
            labelText: 'OCR package URL',
            hintText: 'https://example.org/model.ocrpkg',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(context, controller.text),
              child: const Text('Download & install')),
        ],
      ),
    );
    controller.dispose();
    if (source != null && source.trim().isNotEmpty) {
      await widget.workspace.installRemotePackage(source);
    }
  }

  Future<void> _addRemoteImage() async {
    final controller = TextEditingController();
    final source = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Use remote image'),
        content: TextField(
          controller: controller,
          autofocus: true,
          keyboardType: TextInputType.url,
          decoration: const InputDecoration(
            labelText: 'Image URL',
            hintText: 'https://example.org/manuscript.jpg',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(context, controller.text),
              child: const Text('Download image')),
        ],
      ),
    );
    controller.dispose();
    if (source != null && source.trim().isNotEmpty) {
      await widget.workspace.fetchRemoteImage(source);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.workspace,
      builder: (context, _) {
        final workspace = widget.workspace;
        if (workspace.result != _lastResult) {
          _lastResult = workspace.result;
          _textController.value =
              TextEditingValue(text: workspace.result?.resolvedText ?? '');
          _selectedGlyph = null;
        }
        return Scaffold(
          appBar: AppBar(
            title: const _Brand(),
            actions: [
              IconButton(
                  onPressed: widget.onToggleTheme,
                  icon: const Icon(Icons.contrast_outlined),
                  tooltip: 'Toggle color theme'),
              const SizedBox(width: 4),
            ],
          ),
          body: SafeArea(
            child: LayoutBuilder(
              builder: (context, constraints) {
                final compact = constraints.maxWidth < 980;
                final panels = [
                  _WorkflowPanel(
                    workspace: workspace,
                    onRemotePackage: _addRemotePackage,
                    onRemotePackageArchive: _addRemotePackageArchive,
                    onLocalPackage: _choosePackage,
                    onSelectModel: workspace.selectModel,
                    onRemoveModel: workspace.removeModel,
                    onCheckUpdate: workspace.checkForUpdate,
                  ),
                  _InputPanel(
                    workspace: workspace,
                    onGallery: () => _chooseImage(ImageSource.gallery),
                    onCamera: () => _chooseImage(ImageSource.camera),
                    onFile: _chooseImageFile,
                    onRemote: _addRemoteImage,
                  ),
                  _RunPanel(workspace: workspace, onRun: workspace.run),
                ];
                return ListView(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 40),
                  children: [
                    const _Intro(),
                    const SizedBox(height: 18),
                    if (compact)
                      ...panels.expand(
                          (panel) => [panel, const SizedBox(height: 14)])
                    else
                      Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(child: panels[0]),
                            const SizedBox(width: 14),
                            Expanded(child: panels[1]),
                            const SizedBox(width: 14),
                            Expanded(child: panels[2]),
                          ]),
                    if (!compact) const SizedBox(height: 18),
                    if (workspace.transferProgress != null &&
                        workspace.status == OcrWorkspaceStatus.downloading)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 14),
                        child: LinearProgressIndicator(
                            value: workspace.transferProgress),
                      ),
                    if (workspace.message != null)
                      _StatusNotice(
                          status: workspace.status,
                          message: workspace.message!),
                    const SizedBox(height: 18),
                    _AdvancedControls(workspace: workspace),
                    const SizedBox(height: 18),
                    _ResultsPanel(
                      workspace: workspace,
                      textController: _textController,
                      selectedGlyph: _selectedGlyph,
                      showBoxes: _showBoxes,
                      showLabels: _showLabels,
                      showConfidence: _showConfidence,
                      showUnicode: _showUnicode,
                      onSelectGlyph: (glyph) =>
                          setState(() => _selectedGlyph = glyph),
                      onShowBoxes: (value) =>
                          setState(() => _showBoxes = value),
                      onShowLabels: (value) =>
                          setState(() => _showLabels = value),
                      onShowConfidence: (value) =>
                          setState(() => _showConfidence = value),
                      onShowUnicode: (value) =>
                          setState(() => _showUnicode = value),
                    ),
                  ],
                );
              },
            ),
          ),
        );
      },
    );
  }
}

class _Brand extends StatelessWidget {
  const _Brand();

  @override
  Widget build(BuildContext context) =>
      Row(mainAxisSize: MainAxisSize.min, children: [
        Container(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primary,
              borderRadius: BorderRadius.circular(9)),
          child: Icon(Icons.document_scanner_outlined,
              color: Theme.of(context).colorScheme.onPrimary, size: 18),
        ),
        const SizedBox(width: 9),
        const Text('OCR Runtime'),
      ]);
}

class _Intro extends StatelessWidget {
  const _Intro();

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [
            Theme.of(context).colorScheme.primaryContainer,
            Theme.of(context).colorScheme.surface
          ]),
          borderRadius: BorderRadius.circular(22),
        ),
        child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Transcribe any supported writing system.',
                  style: TextStyle(fontSize: 26, fontWeight: FontWeight.w700)),
              SizedBox(height: 8),
              Text(
                  'Install a self-describing OCR package, select a manuscript image, and review a local, traceable transcription. The app is the runtime; the package supplies the model and alphabet.'),
            ]),
      );
}

class _WorkflowPanel extends StatelessWidget {
  const _WorkflowPanel({
    required this.workspace,
    required this.onRemotePackage,
    required this.onRemotePackageArchive,
    required this.onLocalPackage,
    required this.onSelectModel,
    required this.onRemoveModel,
    required this.onCheckUpdate,
  });

  final OcrWorkspaceController workspace;
  final VoidCallback onRemotePackage;
  final VoidCallback onRemotePackageArchive;
  final VoidCallback onLocalPackage;
  final ValueChanged<InstalledModel> onSelectModel;
  final ValueChanged<InstalledModel> onRemoveModel;
  final VoidCallback onCheckUpdate;

  @override
  Widget build(BuildContext context) => _Panel(
        icon: Icons.layers_outlined,
        title: '1. OCR package',
        subtitle:
            'The package defines the script, alphabet, model, and preprocessing contract.',
        child:
            Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          if (workspace.installedModels.isEmpty)
            const _EmptyHint(
                icon: Icons.inventory_2_outlined,
                text: 'No OCR package installed yet.')
          else
            DropdownButtonFormField<String>(
              initialValue: workspace.activeModel?.manifest.identity,
              decoration: const InputDecoration(
                  labelText: 'Active package', border: OutlineInputBorder()),
              items: workspace.installedModels
                  .map((model) => DropdownMenuItem(
                      value: model.manifest.identity,
                      child: Text(
                          '${model.manifest.displayName} · v${model.manifest.version}',
                          overflow: TextOverflow.ellipsis)))
                  .toList(),
              onChanged: workspace.status == OcrWorkspaceStatus.loadingModels
                  ? null
                  : (identity) {
                      final selected = workspace.installedModels
                          .where((model) => model.manifest.identity == identity)
                          .firstOrNull;
                      if (selected != null) onSelectModel(selected);
                    },
            ),
          if (workspace.activeModel != null) ...[
            const SizedBox(height: 10),
            _ModelDetails(model: workspace.activeModel!),
          ],
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: [
            OutlinedButton.icon(
                onPressed: onRemotePackage,
                icon: const Icon(Icons.link),
                label: const Text('Manifest URL')),
            OutlinedButton.icon(
                onPressed: onRemotePackageArchive,
                icon: const Icon(Icons.cloud_download_outlined),
                label: const Text('Package URL')),
            OutlinedButton.icon(
                onPressed: onLocalPackage,
                icon: const Icon(Icons.upload_file_outlined),
                label: const Text('Import package')),
            if (workspace.activeModel?.manifest.sourceUri?.scheme == 'https')
              TextButton.icon(
                  onPressed: onCheckUpdate,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Check update')),
            if (workspace.activeModel != null &&
                workspace.installedModels.length > 1)
              TextButton.icon(
                  onPressed: () => onRemoveModel(workspace.activeModel!),
                  icon: const Icon(Icons.delete_outline),
                  label: const Text('Remove')),
          ]),
        ]),
      );
}

class _ModelDetails extends StatelessWidget {
  const _ModelDetails({required this.model});
  final InstalledModel model;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerLow,
            borderRadius: BorderRadius.circular(12)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(
              '${model.manifest.alphabet.length} classes · ${model.manifest.modelFormat.name.toUpperCase()} · ${model.manifest.input.width}×${model.manifest.input.height}',
              style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 4),
          Text(
              'Alphabet v${model.manifest.alphabetVersion} · ${model.manifest.readingDirection == ReadingDirection.rightToLeft ? 'RTL' : 'LTR'}',
              style: Theme.of(context).textTheme.bodySmall),
        ]),
      );
}

class _InputPanel extends StatelessWidget {
  const _InputPanel(
      {required this.workspace,
      required this.onGallery,
      required this.onCamera,
      required this.onFile,
      required this.onRemote});
  final OcrWorkspaceController workspace;
  final VoidCallback onGallery;
  final VoidCallback onCamera;
  final VoidCallback onFile;
  final VoidCallback onRemote;

  @override
  Widget build(BuildContext context) => _Panel(
        icon: Icons.image_search_outlined,
        title: '2. Input image',
        subtitle:
            'Use a photo, camera capture, or a validated remote image. Inference stays on-device.',
        child:
            Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Container(
            height: 120,
            decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerLow,
                borderRadius: BorderRadius.circular(14)),
            clipBehavior: Clip.antiAlias,
            child: workspace.imagePath == null
                ? const _EmptyHint(
                    icon: Icons.add_photo_alternate_outlined,
                    text: 'No image selected')
                : Image.file(File(workspace.imagePath!),
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const _EmptyHint(
                        icon: Icons.broken_image_outlined,
                        text: 'Image unavailable')),
          ),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: [
            OutlinedButton.icon(
                onPressed: onGallery,
                icon: const Icon(Icons.photo_library_outlined),
                label: const Text('Gallery')),
            OutlinedButton.icon(
                onPressed: onCamera,
                icon: const Icon(Icons.photo_camera_outlined),
                label: const Text('Camera')),
            OutlinedButton.icon(
                onPressed: onFile,
                icon: const Icon(Icons.folder_open_outlined),
                label: const Text('Files')),
            OutlinedButton.icon(
                onPressed: onRemote,
                icon: const Icon(Icons.language_outlined),
                label: const Text('Image URL')),
          ]),
        ]),
      );
}

class _RunPanel extends StatelessWidget {
  const _RunPanel({required this.workspace, required this.onRun});
  final OcrWorkspaceController workspace;
  final VoidCallback onRun;

  @override
  Widget build(BuildContext context) {
    final running = workspace.status == OcrWorkspaceStatus.running;
    final ready = workspace.activeModel != null &&
        workspace.imagePath != null &&
        !running;
    return _Panel(
      icon: Icons.bolt_outlined,
      title: '3. Run & review',
      subtitle:
          'Detection order is reconstructed into lines and every character remains inspectable.',
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        FilledButton.icon(
          onPressed: ready ? onRun : null,
          icon: running
              ? const SizedBox.square(
                  dimension: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.play_arrow_rounded),
          label: Text(running ? 'Running OCR…' : 'Run on-device OCR'),
        ),
        const SizedBox(height: 14),
        const _SafetyStatement(),
      ]),
    );
  }
}

class _SafetyStatement extends StatelessWidget {
  const _SafetyStatement();

  @override
  Widget build(BuildContext context) =>
      Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(Icons.shield_outlined,
            size: 18, color: Theme.of(context).colorScheme.primary),
        const SizedBox(width: 8),
        const Expanded(
            child: Text(
                'Package checks, alphabet alignment, SHA-256 verification, and atomic activation protect the active model.',
                style: TextStyle(fontSize: 12))),
      ]);
}

class _AdvancedControls extends StatelessWidget {
  const _AdvancedControls({required this.workspace});
  final OcrWorkspaceController workspace;

  @override
  Widget build(BuildContext context) => Card(
        clipBehavior: Clip.antiAlias,
        child: ExpansionTile(
          leading: const Icon(Icons.tune_outlined),
          title: const Text('Research controls'),
          subtitle: const Text(
              'Confidence and suppression thresholds affect displayed detections, not model accuracy.'),
          childrenPadding: const EdgeInsets.fromLTRB(18, 0, 18, 18),
          children: [
            _ThresholdSlider(
              label: 'Confidence threshold',
              value: workspace.configuration.confidenceThreshold,
              onChanged: (value) =>
                  workspace.updateConfiguration(confidenceThreshold: value),
            ),
            _ThresholdSlider(
              label: 'IoU / NMS threshold',
              value: workspace.configuration.iouThreshold,
              onChanged: (value) =>
                  workspace.updateConfiguration(iouThreshold: value),
            ),
            Align(
                alignment: Alignment.centerLeft,
                child: Text(
                    'Maximum detections: ${workspace.configuration.maxDetections}',
                    style: Theme.of(context).textTheme.bodySmall)),
          ],
        ),
      );
}

class _ThresholdSlider extends StatelessWidget {
  const _ThresholdSlider(
      {required this.label, required this.value, required this.onChanged});
  final String label;
  final double value;
  final ValueChanged<double> onChanged;

  @override
  Widget build(BuildContext context) =>
      Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('$label · ${value.toStringAsFixed(2)}'),
        Slider(
            value: value,
            min: 0.05,
            max: 0.95,
            divisions: 18,
            label: value.toStringAsFixed(2),
            onChanged: onChanged),
      ]);
}

class _ResultsPanel extends StatelessWidget {
  const _ResultsPanel({
    required this.workspace,
    required this.textController,
    required this.selectedGlyph,
    required this.showBoxes,
    required this.showLabels,
    required this.showConfidence,
    required this.showUnicode,
    required this.onSelectGlyph,
    required this.onShowBoxes,
    required this.onShowLabels,
    required this.onShowConfidence,
    required this.onShowUnicode,
  });

  final OcrWorkspaceController workspace;
  final TextEditingController textController;
  final GlyphDetection? selectedGlyph;
  final bool showBoxes;
  final bool showLabels;
  final bool showConfidence;
  final bool showUnicode;
  final ValueChanged<GlyphDetection> onSelectGlyph;
  final ValueChanged<bool> onShowBoxes;
  final ValueChanged<bool> onShowLabels;
  final ValueChanged<bool> onShowConfidence;
  final ValueChanged<bool> onShowUnicode;

  @override
  Widget build(BuildContext context) {
    final result = workspace.result;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: result == null
            ? const _EmptyHint(
                icon: Icons.fact_check_outlined,
                text:
                    'Your transcription, confidence data, and model traceability will appear here after OCR runs.')
            : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(
                      child: Text('4. Inspect transcription',
                          style: Theme.of(context)
                              .textTheme
                              .titleLarge
                              ?.copyWith(fontWeight: FontWeight.w700))),
                  PopupMenuButton<OcrExportFormat>(
                    tooltip: 'Export result',
                    onSelected: (format) => workspace.export(format),
                    itemBuilder: (context) => const [
                      PopupMenuItem(
                          value: OcrExportFormat.text,
                          child: Text('Export TXT')),
                      PopupMenuItem(
                          value: OcrExportFormat.json,
                          child: Text('Export research JSON')),
                      PopupMenuItem(
                          value: OcrExportFormat.csv,
                          child: Text('Export glyph CSV')),
                    ],
                    icon: const Icon(Icons.ios_share_outlined),
                  ),
                ]),
                const SizedBox(height: 4),
                Text(
                    '${result.orderedText.detections.length} glyphs · ${(result.orderedText.readingConfidence * 100).toStringAsFixed(1)}% mean confidence · ${result.inferenceTime.inMilliseconds} ms',
                    style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 16),
                LayoutBuilder(builder: (context, constraints) {
                  final compact = constraints.maxWidth < 800;
                  final viewer = _ResultImageViewer(
                    result: result,
                    selectedGlyph: selectedGlyph,
                    showBoxes: showBoxes,
                    showLabels: showLabels,
                    showConfidence: showConfidence,
                    showUnicode: showUnicode,
                    onSelectGlyph: onSelectGlyph,
                  );
                  final editor = _TranscriptionEditor(
                      result: result,
                      controller: textController,
                      onChanged: workspace.editText,
                      selectedGlyph: selectedGlyph);
                  return compact
                      ? Column(children: [
                          viewer,
                          const SizedBox(height: 16),
                          editor
                        ])
                      : Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                              Expanded(flex: 6, child: viewer),
                              const SizedBox(width: 16),
                              Expanded(flex: 5, child: editor)
                            ]);
                }),
                const SizedBox(height: 12),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  FilterChip(
                      label: const Text('Boxes'),
                      selected: showBoxes,
                      onSelected: onShowBoxes),
                  FilterChip(
                      label: const Text('Labels'),
                      selected: showLabels,
                      onSelected: onShowLabels),
                  FilterChip(
                      label: const Text('Confidence'),
                      selected: showConfidence,
                      onSelected: onShowConfidence),
                  FilterChip(
                      label: const Text('Unicode'),
                      selected: showUnicode,
                      onSelected: onShowUnicode),
                ]),
                const SizedBox(height: 14),
                _ReproducibilityMetadata(result: result),
              ]),
      ),
    );
  }
}

class _ResultImageViewer extends StatelessWidget {
  const _ResultImageViewer({
    required this.result,
    required this.selectedGlyph,
    required this.showBoxes,
    required this.showLabels,
    required this.showConfidence,
    required this.showUnicode,
    required this.onSelectGlyph,
  });

  final OcrResult result;
  final GlyphDetection? selectedGlyph;
  final bool showBoxes;
  final bool showLabels;
  final bool showConfidence;
  final bool showUnicode;
  final ValueChanged<GlyphDetection> onSelectGlyph;

  @override
  Widget build(BuildContext context) => AspectRatio(
        aspectRatio: result.imageWidth / result.imageHeight,
        child: LayoutBuilder(builder: (context, constraints) {
          return Container(
            clipBehavior: Clip.antiAlias,
            decoration: BoxDecoration(
                color: Colors.black, borderRadius: BorderRadius.circular(14)),
            child: Stack(fit: StackFit.expand, children: [
              Image.file(File(result.inputPath),
                  fit: BoxFit.fill,
                  errorBuilder: (_, __, ___) => const Center(
                      child: Icon(Icons.broken_image_outlined,
                          color: Colors.white))),
              if (showBoxes)
                ...result.orderedText.detections.map((glyph) {
                  final selected = identical(selectedGlyph, glyph);
                  final left =
                      glyph.left / result.imageWidth * constraints.maxWidth;
                  final top =
                      glyph.top / result.imageHeight * constraints.maxHeight;
                  final width = glyph.boundingBox.width /
                      result.imageWidth *
                      constraints.maxWidth;
                  final height = glyph.boundingBox.height /
                      result.imageHeight *
                      constraints.maxHeight;
                  return Positioned(
                    left: left,
                    top: top,
                    width: width.clamp(3, constraints.maxWidth),
                    height: height.clamp(3, constraints.maxHeight),
                    child: Tooltip(
                      message:
                          '${glyph.glyph.label} · ${(glyph.confidence * 100).toStringAsFixed(1)}%',
                      child: InkWell(
                        onTap: () => onSelectGlyph(glyph),
                        child: Container(
                          decoration: BoxDecoration(
                              border: Border.all(
                                  color: selected
                                      ? Colors.amber
                                      : Colors.lightGreenAccent,
                                  width: selected ? 3 : 1.5)),
                          alignment: Alignment.topLeft,
                          child: showLabels
                              ? Container(
                                  color: Colors.black.withValues(alpha: .72),
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 3, vertical: 1),
                                  child: Text(
                                    [
                                      glyph.glyph.display ?? glyph.glyph.label,
                                      if (showUnicode) glyph.glyph.unicode,
                                      if (showConfidence)
                                        '${(glyph.confidence * 100).toStringAsFixed(0)}%'
                                    ].join(' '),
                                    style: const TextStyle(
                                        fontSize: 10, color: Colors.white),
                                    overflow: TextOverflow.clip,
                                  ),
                                )
                              : null,
                        ),
                      ),
                    ),
                  );
                }),
            ]),
          );
        }),
      );
}

class _TranscriptionEditor extends StatelessWidget {
  const _TranscriptionEditor(
      {required this.result,
      required this.controller,
      required this.onChanged,
      required this.selectedGlyph});
  final OcrResult result;
  final TextEditingController controller;
  final ValueChanged<String> onChanged;
  final GlyphDetection? selectedGlyph;

  @override
  Widget build(BuildContext context) =>
      Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        TextField(
          controller: controller,
          minLines: 5,
          maxLines: 12,
          onChanged: onChanged,
          decoration: InputDecoration(
            labelText: 'Editable transcription',
            helperText: result.hasCorrections
                ? 'Edited text is preserved separately from raw model output.'
                : 'Raw model output; edits create a separate corrected transcription.',
            border: const OutlineInputBorder(),
          ),
          style: const TextStyle(fontSize: 20),
        ),
        const SizedBox(height: 12),
        if (selectedGlyph == null)
          const _EmptyHint(
              icon: Icons.ads_click_outlined,
              text:
                  'Select a glyph in the image to inspect its class mapping and alternatives.')
        else
          _GlyphInspector(glyph: selectedGlyph!),
      ]);
}

class _GlyphInspector extends StatelessWidget {
  const _GlyphInspector({required this.glyph});
  final GlyphDetection glyph;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.secondaryContainer,
            borderRadius: BorderRadius.circular(12)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Text(glyph.glyph.display ?? glyph.glyph.label,
                style: const TextStyle(fontSize: 28)),
            const SizedBox(width: 10),
            Expanded(
                child: Text(
                    '${glyph.glyph.unicode} · class ${glyph.glyph.id}\n${(glyph.confidence * 100).toStringAsFixed(1)}% confidence')),
          ]),
          if (glyph.glyph.name != null)
            Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(glyph.glyph.name!)),
          if (glyph.alternatives.length > 1) ...[
            const SizedBox(height: 8),
            Text('Model alternatives',
                style: Theme.of(context).textTheme.labelLarge),
            Wrap(
                spacing: 6,
                children: glyph.alternatives
                    .map((item) => Chip(
                        label: Text(
                            '${item.glyph.display ?? item.glyph.label} ${(item.confidence * 100).toStringAsFixed(0)}%')))
                    .toList()),
          ],
        ]),
      );
}

class _ReproducibilityMetadata extends StatelessWidget {
  const _ReproducibilityMetadata({required this.result});
  final OcrResult result;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
            border:
                Border.all(color: Theme.of(context).colorScheme.outlineVariant),
            borderRadius: BorderRadius.circular(12)),
        child: Wrap(spacing: 16, runSpacing: 6, children: [
          _Metadata(
              label: 'Package',
              value:
                  '${result.model.manifest.packageId} v${result.model.manifest.version}'),
          _Metadata(
              label: 'Alphabet', value: result.model.manifest.alphabetVersion),
          _Metadata(label: 'Model', value: result.model.manifest.modelVersion),
          _Metadata(
              label: 'Run',
              value: result.createdAt.toLocal().toString().split('.').first),
          _Metadata(
              label: 'Threshold',
              value:
                  result.configuration.confidenceThreshold.toStringAsFixed(2)),
        ]),
      );
}

class _Metadata extends StatelessWidget {
  const _Metadata({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => RichText(
          text:
              TextSpan(style: Theme.of(context).textTheme.bodySmall, children: [
        TextSpan(
            text: '$label: ',
            style: const TextStyle(fontWeight: FontWeight.bold)),
        TextSpan(text: value)
      ]));
}

class _Panel extends StatelessWidget {
  const _Panel(
      {required this.icon,
      required this.title,
      required this.subtitle,
      required this.child});
  final IconData icon;
  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(18),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Icon(icon, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 8),
              Expanded(
                  child: Text(title,
                      style: Theme.of(context)
                          .textTheme
                          .titleMedium
                          ?.copyWith(fontWeight: FontWeight.w700)))
            ]),
            const SizedBox(height: 7),
            Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 15),
            child,
          ]),
        ),
      );
}

class _StatusNotice extends StatelessWidget {
  const _StatusNotice({required this.status, required this.message});
  final OcrWorkspaceStatus status;
  final String message;

  @override
  Widget build(BuildContext context) {
    final isFailure = status == OcrWorkspaceStatus.failed;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
          color: isFailure
              ? Theme.of(context).colorScheme.errorContainer
              : Theme.of(context).colorScheme.secondaryContainer,
          borderRadius: BorderRadius.circular(12)),
      child: Row(children: [
        Icon(isFailure ? Icons.error_outline : Icons.info_outline),
        const SizedBox(width: 10),
        Expanded(child: Text(message))
      ]),
    );
  }
}

class _EmptyHint extends StatelessWidget {
  const _EmptyHint({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(14),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(icon, size: 20, color: Theme.of(context).colorScheme.outline),
          const SizedBox(width: 8),
          Flexible(
              child: Text(text,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall))
        ]),
      );
}
