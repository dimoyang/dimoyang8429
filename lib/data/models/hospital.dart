/// 医院信息（对应后端 HospitalResponse，仅保留映射所需字段）。
class HospitalInfo {
  final int id;
  final String name;
  final String nameEn;
  final String level;

  const HospitalInfo({
    required this.id,
    required this.name,
    this.nameEn = '',
    this.level = '',
  });

  factory HospitalInfo.fromJson(Map<String, dynamic> json) {
    return HospitalInfo(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      nameEn: json['name_en'] as String? ?? '',
      level: json['level'] as String? ?? '',
    );
  }
}
