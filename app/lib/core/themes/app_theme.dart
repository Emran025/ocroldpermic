import 'package:flutter/material.dart';

import '../constants/app_colors.dart';

enum AppThemeType { light, dark, reading }

abstract final class AppThemes {
  static ThemeData getTheme(AppThemeType type) {
    switch (type) {
      case AppThemeType.light:
        return _build(Brightness.light, AppColors.paper, AppColors.graphite);
      case AppThemeType.dark:
        return _build(Brightness.dark, AppColors.ink, AppColors.paper);
      case AppThemeType.reading:
        return _build(
            Brightness.light, AppColors.readingPaper, AppColors.readingInk,
            reading: true);
    }
  }

  static ThemeMode getThemeMode(AppThemeType type) =>
      type == AppThemeType.dark ? ThemeMode.dark : ThemeMode.light;

  static ThemeData _build(
      Brightness brightness, Color background, Color foreground,
      {bool reading = false}) {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.olive,
      brightness: brightness,
      surface: background,
      onSurface: foreground,
      primary: reading ? AppColors.graphite : AppColors.olive,
      onPrimary: AppColors.paper,
      secondary: reading ? AppColors.olive : AppColors.graphite,
      onSecondary: AppColors.paper,
      error: AppColors.error,
    );
    final text = ThemeData(brightness: brightness)
        .textTheme
        .apply(bodyColor: foreground, displayColor: foreground);
    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: background,
      textTheme: text.copyWith(
        headlineLarge: text.headlineLarge
            ?.copyWith(fontWeight: FontWeight.w700, letterSpacing: -.4),
        titleLarge: text.titleLarge?.copyWith(fontWeight: FontWeight.w700),
        titleMedium: text.titleMedium?.copyWith(fontWeight: FontWeight.w600),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: background.withValues(alpha: .94),
        foregroundColor: foreground,
        elevation: 0,
        scrolledUnderElevation: 0,
        titleTextStyle: text.titleLarge
            ?.copyWith(fontWeight: FontWeight.w700, color: foreground),
        iconTheme: IconThemeData(color: foreground),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        margin: EdgeInsets.zero,
        color: background,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
            side: BorderSide(color: scheme.outlineVariant)),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: brightness == Brightness.dark
            ? AppColors.graphite
            : AppColors.paper,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      ),
      filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
              minimumSize: const Size(44, 46),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)))),
      outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
              minimumSize: const Size(44, 44),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)))),
      chipTheme: ChipThemeData(
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
    );
  }
}
