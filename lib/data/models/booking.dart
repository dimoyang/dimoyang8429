/// 预约请求（对应后端 BookingCreate）。
class BookingRequest {
  final int packageId;
  final DateTime appointmentDate;
  final String contactName;
  final String contactPhone;
  final String contactEmail;
  final String notes;
  final bool needTranslator;
  final bool needAccommodation;
  final bool needPickup;

  const BookingRequest({
    required this.packageId,
    required this.appointmentDate,
    required this.contactName,
    required this.contactPhone,
    required this.contactEmail,
    this.notes = '',
    this.needTranslator = false,
    this.needAccommodation = false,
    this.needPickup = false,
  });

  Map<String, dynamic> toJson() {
    return {
      'package_id': packageId,
      'appointment_date': appointmentDate.toIso8601String(),
      'contact_name': contactName,
      'contact_phone': contactPhone,
      'contact_email': contactEmail,
      'notes': notes,
      'need_translator': needTranslator,
      'need_accommodation': needAccommodation,
      'need_pickup': needPickup,
    };
  }
}

/// 我的预约订单（对应后端 GET /bookings/ 列表项）。
///
/// 后端列表接口目前只返回部分字段，`package_id`、`appointment_date`、`created_at`
/// 按可选解析，缺失时不影响列表展示。
class BookingOrder {
  final int id;
  final String orderNo;
  final int? packageId;
  final DateTime? appointmentDate;
  final double totalPrice;
  final String currency;
  final String status;
  final DateTime? createdAt;

  const BookingOrder({
    required this.id,
    required this.orderNo,
    this.packageId,
    this.appointmentDate,
    required this.totalPrice,
    required this.currency,
    required this.status,
    this.createdAt,
  });

  factory BookingOrder.fromJson(Map<String, dynamic> json) {
    return BookingOrder(
      id: (json['id'] as num?)?.toInt() ?? 0,
      orderNo: json['order_no'] as String? ?? '',
      packageId: (json['package_id'] as num?)?.toInt(),
      appointmentDate: _parseDate(json['appointment_date']),
      totalPrice: (json['total_price'] as num? ?? 0).toDouble(),
      currency: json['currency'] as String? ?? '',
      status: json['status'] as String? ?? '',
      createdAt: _parseDate(json['created_at']),
    );
  }

  static DateTime? _parseDate(dynamic value) {
    if (value is! String || value.isEmpty) {
      return null;
    }
    return DateTime.tryParse(value);
  }
}

/// 预约结果（对应后端 BookingResponse 的展示所需字段）。
class BookingResult {
  final int id;
  final String orderNo;
  final double totalPrice;
  final String currency;
  final String status;

  const BookingResult({
    required this.id,
    required this.orderNo,
    required this.totalPrice,
    required this.currency,
    required this.status,
  });

  factory BookingResult.fromJson(Map<String, dynamic> json) {
    return BookingResult(
      id: json['id'] as int,
      orderNo: json['order_no'] as String? ?? '',
      totalPrice: (json['total_price'] as num? ?? 0).toDouble(),
      currency: json['currency'] as String? ?? '',
      status: json['status'] as String? ?? '',
    );
  }
}
