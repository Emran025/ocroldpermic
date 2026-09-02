import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'application/composition.dart';
import 'application/model_update.dart';

void main() => runApp(const OldPermicApp());

class OldPermicApp extends StatefulWidget {
  const OldPermicApp({super.key, this.initialUpdateCheck = true});
  final bool initialUpdateCheck;
  @override State<OldPermicApp> createState() => _OldPermicAppState();
}

class _OldPermicAppState extends State<OldPermicApp> {
  ThemeMode mode = ThemeMode.system;
  final dependencies = AppDependencies.create();
  @override Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'مختبر OCR للبرمية القديمة',
    themeMode: mode,
    theme: ThemeData(colorSchemeSeed: const Color(0xffb67a18), brightness: Brightness.light, useMaterial3: true, fontFamily: 'sans'),
    darkTheme: ThemeData(colorSchemeSeed: const Color(0xffd7a548), brightness: Brightness.dark, useMaterial3: true, fontFamily: 'sans'),
    home: TrialPage(dependencies: dependencies, initialUpdateCheck: widget.initialUpdateCheck, onToggleTheme: () => setState(() => mode = mode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark)),
  );
}

class TrialPage extends StatefulWidget {
  const TrialPage({super.key, required this.dependencies, required this.onToggleTheme, this.initialUpdateCheck = true});
  final AppDependencies dependencies;
  final bool initialUpdateCheck;
  final VoidCallback onToggleTheme;
  @override State<TrialPage> createState() => _TrialPageState();
}

class _TrialPageState extends State<TrialPage> {
  XFile? image;
  UpdateState updateState = const UpdateOffline();
  String? error;
  final picker = ImagePicker();

  Future<void> checkUpdate({bool manual = true}) async {
    setState(() { error = null; updateState = const UpdateChecking(); });
    final state = await widget.dependencies.updates.check(manual: manual);
    if (mounted) setState(() => updateState = state);
  }
  Future<void> choose(ImageSource source) async {
    final picked = await picker.pickImage(source: source, imageQuality: 100);
    if (picked != null && mounted) setState(() { image = picked; error = null; });
  }
  @override void initState() { super.initState(); if (widget.initialUpdateCheck) WidgetsBinding.instance.addPostFrameCallback((_) => checkUpdate(manual: false)); }
  @override Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Directionality(textDirection: TextDirection.rtl, child: Scaffold(
      appBar: AppBar(title: const Text('مختبر البرمية القديمة'), actions: [IconButton(onPressed: widget.onToggleTheme, icon: const Icon(Icons.dark_mode_outlined), tooltip: 'تبديل المظهر')]),
      drawer: Drawer(child: SafeArea(child: ListView(padding: const EdgeInsets.all(20), children: [
        Text('Old Permic OCR', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8), const Text('تجربة محلية حرفية، لا ترجمة تلقائية ولا ادعاء أداء تاريخي.'),
        const Divider(height: 32),
        ListTile(leading: const Icon(Icons.sync), title: const Text('تحديث النموذج'), subtitle: Text(_statusLabel(updateState)), onTap: () { Navigator.pop(context); checkUpdate(); }),
        ListTile(leading: const Icon(Icons.brightness_6_outlined), title: const Text('المظهر'), subtitle: const Text('فاتح / داكن'), onTap: widget.onToggleTheme),
      ]))),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        Text('تجربة النموذج', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Text('ارفع صورة أو التقطها. سيجري ترتيب الكشفات حرفيًا، وتبقى النتيجة قابلة للمراجعة قبل النسخ.', style: Theme.of(context).textTheme.bodyLarge),
        const SizedBox(height: 20),
        Card(child: Padding(padding: const EdgeInsets.all(18), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [Icon(Icons.shield_outlined, color: colors.primary), const SizedBox(width: 8), const Expanded(child: Text('النموذج الصناعي الحالي للاختبار فقط؛ لا يمثل أداءً على مخطوطات تاريخية.'))]),
          const SizedBox(height: 18),
          if (image != null) ClipRRect(borderRadius: BorderRadius.circular(14), child: Image.file(File(image!.path), height: 220, fit: BoxFit.contain)) else Container(height: 180, decoration: BoxDecoration(color: colors.surfaceContainerHighest, borderRadius: BorderRadius.circular(14)), child: const Icon(Icons.image_search_outlined, size: 54)),
          const SizedBox(height: 16),
          Row(children: [Expanded(child: FilledButton.icon(onPressed: () => choose(ImageSource.gallery), icon: const Icon(Icons.photo_library_outlined), label: const Text('اختيار صورة'))), const SizedBox(width: 10), Expanded(child: OutlinedButton.icon(onPressed: () => choose(ImageSource.camera), icon: const Icon(Icons.camera_alt_outlined), label: const Text('التقاط صورة')))]),
          const SizedBox(height: 12),
          FilledButton.icon(onPressed: image == null ? null : () => setState(() => error = 'سيُفعّل محول ONNX المحلي بعد توفر مكتبة Android native في بيئة Flutter.'), icon: const Icon(Icons.document_scanner_outlined), label: const Text('تشغيل التجربة المحلية')),
        ]))),
        const SizedBox(height: 16),
        Card(child: Padding(padding: const EdgeInsets.all(18), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('النص المرتب', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          Text(error ?? 'لا توجد نتيجة بعد. بعد نجاح الاستدلال ستظهر المحارف بترتيبها وثقة القراءة.', style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: 18),
          Text('عدد الكشفات: —    انتظام القراءة: —', style: Theme.of(context).textTheme.bodySmall),
        ]))),
      ]),
    ));
  }
  String _statusLabel(UpdateState state) => switch (state) { UpdateOffline() => 'دون اتصال', UpdateUpToDate() => 'محدّث', UpdateAvailable() => 'تحديث متاح', UpdateActivated() => 'تم التحديث', UpdateFailed(:final message) => message, UpdateChecking() => 'جارٍ الفحص' };
}
