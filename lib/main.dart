import 'package:flutter/material.dart';

import 'application/composition.dart';
import 'core/themes/app_theme.dart';
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
        title: 'ARCHIVAL VISION LAB',
        themeMode: _mode,
        theme: AppThemes.getTheme(AppThemeType.light),
        darkTheme: AppThemes.getTheme(AppThemeType.dark),
        home: OcrWorkspacePage(
          workspace: _dependencies.workspace,
          onToggleTheme: () => setState(() => _mode =
              _mode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark),
        ),
      );
}

/// Compatibility entry point for code importing the former root widget.
@Deprecated('Use OcrRuntimeApp instead.')
class OldPermicApp extends OcrRuntimeApp {
  const OldPermicApp({super.key, super.initialUpdateCheck});
}
