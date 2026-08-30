import 'package:flutter/material.dart';

import 'application/composition.dart';
import 'presentation/pages/ocr_workspace_page.dart';

void main() => runApp(const OcrRuntimeApp());

class OcrRuntimeApp extends StatefulWidget {
  const OcrRuntimeApp({super.key, this.initialUpdateCheck = true});

  final bool initialUpdateCheck;

  @override
  State<OcrRuntimeApp> createState() => _OcrRuntimeAppState();
}

class _OcrRuntimeAppState extends State<OcrRuntimeApp> {
  ThemeMode _mode = ThemeMode.system;
  late final AppDependencies _dependencies = AppDependencies.create();

  @override
  Widget build(BuildContext context) => MaterialApp(
        debugShowCheckedModeBanner: false,
        title: 'OCR Runtime',
        themeMode: _mode,
        theme: _theme(Brightness.light),
        darkTheme: _theme(Brightness.dark),
        home: OcrWorkspacePage(
          workspace: _dependencies.workspace,
          onToggleTheme: () => setState(() => _mode =
              _mode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark),
        ),
      );

  ThemeData _theme(Brightness brightness) {
    final scheme = ColorScheme.fromSeed(
        seedColor: const Color(0xff2455a4), brightness: brightness);
    return ThemeData(
      colorScheme: scheme,
      brightness: brightness,
      useMaterial3: true,
      scaffoldBackgroundColor:
          brightness == Brightness.light ? const Color(0xfff7f8fc) : null,
      cardTheme: CardThemeData(
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
            side: BorderSide(color: scheme.outlineVariant)),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: scheme.surface,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      ),
    );
  }
}

/// Temporary compatibility entry point for code importing the old root widget.
@Deprecated('Use OcrRuntimeApp instead.')
class OldPermicApp extends OcrRuntimeApp {
  const OldPermicApp({super.key, super.initialUpdateCheck});
}
