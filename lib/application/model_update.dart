import '../domain/entities/release_manifest.dart';
import '../domain/repositories/ocr_ports.dart';

sealed class UpdateState {
  const UpdateState();
}
class UpdateOffline extends UpdateState { const UpdateOffline(); }
class UpdateChecking extends UpdateState { const UpdateChecking(); }
class UpdateUpToDate extends UpdateState { const UpdateUpToDate(this.model); final ActiveModel model; }
class UpdateAvailable extends UpdateState { const UpdateAvailable(this.release); final ReleaseManifest release; }
class UpdateActivated extends UpdateState { const UpdateActivated(this.model); final ActiveModel model; }
class UpdateFailed extends UpdateState { const UpdateFailed(this.message); final String message; }

class ModelUpdateController {
  ModelUpdateController(this.network, this.releases, this.models, {DateTime Function()? clock}) : _clock = clock ?? DateTime.now;
  static const interval = Duration(minutes: 10);
  final NetworkRepository network;
  final ReleaseRepository releases;
  final ModelStore models;
  final DateTime Function() _clock;
  DateTime? _lastAutomaticCheck;
  Future<UpdateState>? _inFlight;
  ReleaseManifest? _pending;

  Future<UpdateState> check({bool manual = false}) {
    if (_inFlight != null) return _inFlight!;
    final now = _clock();
    if (!manual && _lastAutomaticCheck != null && now.difference(_lastAutomaticCheck!) < interval) {
      return Future.value(const UpdateFailed('تم تأجيل الفحص التلقائي حتى انتهاء فترة العشر دقائق.'));
    }
    _lastAutomaticCheck = now;
    final operation = _check();
    _inFlight = operation;
    operation.whenComplete(() => _inFlight = null);
    return operation;
  }

  Future<UpdateState> _check() async {
    if (!await network.isOnline()) return const UpdateOffline();
    try {
      final release = await releases.fetchLatest();
      final current = await models.active();
      if (current?.release.releaseId == release.releaseId) return UpdateUpToDate(current!);
      _pending = release;
      return UpdateAvailable(release);
    } catch (error) {
      return UpdateFailed(error.toString());
    }
  }

  Future<UpdateState> activatePending() async {
    final release = _pending;
    if (release == null) return const UpdateFailed('لا يوجد تحديث متحقق للتنشيط.');
    try {
      final active = await models.stageAndActivate(release);
      _pending = null;
      return UpdateActivated(active);
    } catch (error) {
      return UpdateFailed(error.toString());
    }
  }
}
