/// Web 之外的平台没有免权限的保存路径，交给 UI 降级处理。
Future<bool> saveExport(String json, {required String filename}) async {
  return false;
}
