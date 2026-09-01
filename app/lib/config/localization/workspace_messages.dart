import 'l10n/app_localizations.dart';

typedef LocalizedMessage = String Function(AppLocalizations l10n);

final class WorkspaceMessage {
  const WorkspaceMessage(this.resolve);
  final LocalizedMessage resolve;
}

abstract final class WorkspaceMessages {
  static WorkspaceMessage raw(String value) => WorkspaceMessage((_) => value);
  static final packagesLoad = WorkspaceMessage((l) => l.noPackagesLoaded);
  static final invalidImageUrl = WorkspaceMessage((l) => l.invalidImageUrl);
  static final downloadingImage = WorkspaceMessage((l) => l.downloadingImage);
  static final imageDownloadFailed =
      WorkspaceMessage((l) => l.imageDownloadFailed);
  static final invalidManifestUrl =
      WorkspaceMessage((l) => l.invalidManifestUrl);
  static final checkingPackage = WorkspaceMessage((l) => l.checkingPackage);
  static final downloadingPackage =
      WorkspaceMessage((l) => l.downloadingPackage);
  static WorkspaceMessage ready(String name) =>
      WorkspaceMessage((l) => l.ocrPackageReady(name));
  static final invalidRemotePackage =
      WorkspaceMessage((l) => l.invalidRemotePackage);
  static final missingPackage = WorkspaceMessage((l) => l.missingPackage);
  static final validatingPackage = WorkspaceMessage((l) => l.validatingPackage);
  static final invalidLocalPackage =
      WorkspaceMessage((l) => l.invalidLocalPackage);
  static WorkspaceMessage activating(String name) =>
      WorkspaceMessage((l) => l.activatingPackage(name));
  static final activationFailed = WorkspaceMessage((l) => l.activationFailed);
  static final removeActiveFailed =
      WorkspaceMessage((l) => l.removeActiveFailed);
  static final selectPackageFirst =
      WorkspaceMessage((l) => l.selectPackageFirst);
  static final selectImageFirst = WorkspaceMessage((l) => l.selectImageFirst);
  static final ocrRunning = WorkspaceMessage((l) => l.ocrRunning);
  static final noGlyphs = WorkspaceMessage((l) => l.noGlyphs);
  static final ocrFailed = WorkspaceMessage((l) => l.ocrFailed);
  static WorkspaceMessage exportCreated(String path) =>
      WorkspaceMessage((l) => l.exportCreated(path));
  static final exportFailed = WorkspaceMessage((l) => l.exportFailed);
  static final checkingUpdates = WorkspaceMessage((l) => l.checkingUpdates);
  static final offline = WorkspaceMessage((l) => l.offline);
  static final upToDate = WorkspaceMessage((l) => l.activeUpToDate);
  static WorkspaceMessage updateAvailable(String version) =>
      WorkspaceMessage((l) => l.updateAvailable(version));
  static WorkspaceMessage updated(String name) =>
      WorkspaceMessage((l) => l.packageUpdated(name));
  static final installingUpdate = WorkspaceMessage((l) => l.installingUpdate);
}
