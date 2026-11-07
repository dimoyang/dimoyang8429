import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/network/api_service.dart';
import 'package:meditour_app/data/models/booking.dart';

/// 预约订单仓库：把应用内的字符串 id 转换为后端整型 package_id 后提交。
class BookingRepository {
  BookingRepository._();

  /// 当前登录用户的预约订单列表。
  static Future<List<BookingOrder>> list() async {
    final items = await ApiService.instance.getMyBookings();
    return items.map(BookingOrder.fromJson).toList();
  }

  static Future<BookingResult> create({
    required String serviceId,
    required DateTime date,
    required String contactName,
    required String contactPhone,
    required String contactEmail,
    String notes = '',
    bool needTranslator = false,
    bool needAccommodation = false,
    bool needPickup = false,
  }) async {
    final packageId = int.tryParse(serviceId);
    if (packageId == null) {
      throw const InvalidArgumentException();
    }

    // 固定到当天 9 点，避免零点时间被时区换算偏移日期。
    final appointment = DateTime(date.year, date.month, date.day, 9);

    final data = await ApiService.instance.createBooking(
      BookingRequest(
        packageId: packageId,
        appointmentDate: appointment,
        contactName: contactName,
        contactPhone: contactPhone,
        contactEmail: contactEmail,
        notes: notes,
        needTranslator: needTranslator,
        needAccommodation: needAccommodation,
        needPickup: needPickup,
      ).toJson(),
    );
    return BookingResult.fromJson(data);
  }
}
