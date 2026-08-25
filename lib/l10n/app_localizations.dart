import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_de.dart';
import 'app_localizations_en.dart';
import 'app_localizations_fr.dart';
import 'app_localizations_zh.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('de'),
    Locale('en'),
    Locale('fr'),
    Locale('zh')
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'Meditour'**
  String get appTitle;

  /// No description provided for @appSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Your Gateway to China'**
  String get appSubtitle;

  /// No description provided for @tagline.
  ///
  /// In en, this message translates to:
  /// **'From Europe to China'**
  String get tagline;

  /// No description provided for @taglineSubtitle.
  ///
  /// In en, this message translates to:
  /// **'5,000 years of civilization, waiting for you to explore'**
  String get taglineSubtitle;

  /// No description provided for @searchHint.
  ///
  /// In en, this message translates to:
  /// **'Search destinations, attractions, food…'**
  String get searchHint;

  /// No description provided for @searchComingSoon.
  ///
  /// In en, this message translates to:
  /// **'Search will be available in the next version'**
  String get searchComingSoon;

  /// No description provided for @heroTitle.
  ///
  /// In en, this message translates to:
  /// **'Climb the Great Wall · Explore the Forbidden City · Taste Hot Pot'**
  String get heroTitle;

  /// No description provided for @heroSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Visa assistance · Transport booking · Custom itineraries — all in one place'**
  String get heroSubtitle;

  /// No description provided for @chipVisa.
  ///
  /// In en, this message translates to:
  /// **'Visa Assistance'**
  String get chipVisa;

  /// No description provided for @chipTransport.
  ///
  /// In en, this message translates to:
  /// **'Trains & Flights'**
  String get chipTransport;

  /// No description provided for @chipHotel.
  ///
  /// In en, this message translates to:
  /// **'Hotel Booking'**
  String get chipHotel;

  /// No description provided for @chipItinerary.
  ///
  /// In en, this message translates to:
  /// **'Custom Itinerary'**
  String get chipItinerary;

  /// No description provided for @chipComingSoon.
  ///
  /// In en, this message translates to:
  /// **'will be available in the next version'**
  String get chipComingSoon;

  /// No description provided for @sectionDestinations.
  ///
  /// In en, this message translates to:
  /// **'Popular Destinations'**
  String get sectionDestinations;

  /// No description provided for @sectionDestinationsSub.
  ///
  /// In en, this message translates to:
  /// **'4 cities selected'**
  String get sectionDestinationsSub;

  /// No description provided for @sectionTips.
  ///
  /// In en, this message translates to:
  /// **'Travel Tips'**
  String get sectionTips;

  /// No description provided for @tipPayment.
  ///
  /// In en, this message translates to:
  /// **'China is fully cashless — exchange a small amount at the airport for emergencies; major hotels and duty-free shops accept foreign cards'**
  String get tipPayment;

  /// No description provided for @tipSim.
  ///
  /// In en, this message translates to:
  /// **'Get a Chinese SIM card or eSIM before departure for easy scanning, translation, and navigation'**
  String get tipSim;

  /// No description provided for @medicalEntryTitle.
  ///
  /// In en, this message translates to:
  /// **'Health Concierge'**
  String get medicalEntryTitle;

  /// No description provided for @medicalEntrySub.
  ///
  /// In en, this message translates to:
  /// **'Need medical care during your trip? We\'ve got you covered'**
  String get medicalEntrySub;

  /// No description provided for @footerText.
  ///
  /// In en, this message translates to:
  /// **'Meditour · Making every China journey worry-free'**
  String get footerText;

  /// No description provided for @homeAppBarTitle.
  ///
  /// In en, this message translates to:
  /// **'Discover China'**
  String get homeAppBarTitle;

  /// No description provided for @medicalListTitle.
  ///
  /// In en, this message translates to:
  /// **'Health Concierge'**
  String get medicalListTitle;

  /// No description provided for @medicalListInfo.
  ///
  /// In en, this message translates to:
  /// **'If you have medical needs during your trip, we can connect you with premium healthcare resources. No worries if not — come back anytime to continue exploring.'**
  String get medicalListInfo;

  /// No description provided for @destinationNotFound.
  ///
  /// In en, this message translates to:
  /// **'Destination not found'**
  String get destinationNotFound;

  /// No description provided for @serviceNotFound.
  ///
  /// In en, this message translates to:
  /// **'Service not found'**
  String get serviceNotFound;

  /// No description provided for @sectionImpression.
  ///
  /// In en, this message translates to:
  /// **'City Impression'**
  String get sectionImpression;

  /// No description provided for @sectionExperiences.
  ///
  /// In en, this message translates to:
  /// **'Must-Try Experiences'**
  String get sectionExperiences;

  /// No description provided for @sectionTravelTips.
  ///
  /// In en, this message translates to:
  /// **'Travel Tips'**
  String get sectionTravelTips;

  /// No description provided for @sectionIntro.
  ///
  /// In en, this message translates to:
  /// **'Service Overview'**
  String get sectionIntro;

  /// No description provided for @sectionHighlights.
  ///
  /// In en, this message translates to:
  /// **'Highlights'**
  String get sectionHighlights;

  /// No description provided for @sectionProcess.
  ///
  /// In en, this message translates to:
  /// **'Process'**
  String get sectionProcess;

  /// No description provided for @statBestSeason.
  ///
  /// In en, this message translates to:
  /// **'Best Season'**
  String get statBestSeason;

  /// No description provided for @statSuggestDays.
  ///
  /// In en, this message translates to:
  /// **'Suggested Days'**
  String get statSuggestDays;

  /// No description provided for @statBasePrice.
  ///
  /// In en, this message translates to:
  /// **'Base Price'**
  String get statBasePrice;

  /// No description provided for @statDuration.
  ///
  /// In en, this message translates to:
  /// **'Duration'**
  String get statDuration;

  /// No description provided for @statCompanion.
  ///
  /// In en, this message translates to:
  /// **'Companion'**
  String get statCompanion;

  /// No description provided for @btnItinerary.
  ///
  /// In en, this message translates to:
  /// **'Inquire About Itinerary'**
  String get btnItinerary;

  /// No description provided for @btnBookConsult.
  ///
  /// In en, this message translates to:
  /// **'Book Consultation'**
  String get btnBookConsult;

  /// No description provided for @btnSubmit.
  ///
  /// In en, this message translates to:
  /// **'Submit Booking'**
  String get btnSubmit;

  /// No description provided for @btnBackHome.
  ///
  /// In en, this message translates to:
  /// **'Back to Home'**
  String get btnBackHome;

  /// No description provided for @btnViewService.
  ///
  /// In en, this message translates to:
  /// **'View Service Details'**
  String get btnViewService;

  /// No description provided for @itineraryComingSoon.
  ///
  /// In en, this message translates to:
  /// **'Custom itinerary consultation will be available in the next version'**
  String get itineraryComingSoon;

  /// No description provided for @bookingSuccess.
  ///
  /// In en, this message translates to:
  /// **'Booking Submitted Successfully!'**
  String get bookingSuccess;

  /// No description provided for @bookingSuccessDesc.
  ///
  /// In en, this message translates to:
  /// **'Thank you for your trust! Your medical concierge will contact you within 24 hours via your provided contact method.'**
  String get bookingSuccessDesc;

  /// No description provided for @bookingNo.
  ///
  /// In en, this message translates to:
  /// **'Booking No.'**
  String get bookingNo;

  /// No description provided for @bookingNote.
  ///
  /// In en, this message translates to:
  /// **'🔒 Your information is used solely for this booking. A medical concierge will contact you within 24 hours. This demo does not connect to a real server.'**
  String get bookingNote;

  /// No description provided for @formName.
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get formName;

  /// No description provided for @formNameError.
  ///
  /// In en, this message translates to:
  /// **'Please enter your name'**
  String get formNameError;

  /// No description provided for @formContact.
  ///
  /// In en, this message translates to:
  /// **'Contact (Email / Phone)'**
  String get formContact;

  /// No description provided for @formContactHint.
  ///
  /// In en, this message translates to:
  /// **'For concierge to confirm your itinerary'**
  String get formContactHint;

  /// No description provided for @formContactError.
  ///
  /// In en, this message translates to:
  /// **'Please enter a valid contact'**
  String get formContactError;

  /// No description provided for @formDate.
  ///
  /// In en, this message translates to:
  /// **'Preferred Date'**
  String get formDate;

  /// No description provided for @formDateHint.
  ///
  /// In en, this message translates to:
  /// **'Select a date'**
  String get formDateHint;

  /// No description provided for @formNote.
  ///
  /// In en, this message translates to:
  /// **'Condition / Needs'**
  String get formNote;

  /// No description provided for @formNoteHint.
  ///
  /// In en, this message translates to:
  /// **'Briefly describe your situation (optional)'**
  String get formNoteHint;

  /// No description provided for @daysTreatment.
  ///
  /// In en, this message translates to:
  /// **'{days} days treatment'**
  String daysTreatment(int days);

  /// No description provided for @hospitalLabel.
  ///
  /// In en, this message translates to:
  /// **'Hospital'**
  String get hospitalLabel;

  /// No description provided for @priceLabel.
  ///
  /// In en, this message translates to:
  /// **'Base price'**
  String get priceLabel;

  /// No description provided for @durationLabel.
  ///
  /// In en, this message translates to:
  /// **'Duration'**
  String get durationLabel;

  /// No description provided for @startingFrom.
  ///
  /// In en, this message translates to:
  /// **'from'**
  String get startingFrom;

  /// No description provided for @level3A.
  ///
  /// In en, this message translates to:
  /// **'Grade 3A'**
  String get level3A;

  /// No description provided for @navDiscover.
  ///
  /// In en, this message translates to:
  /// **'Discover'**
  String get navDiscover;

  /// No description provided for @navItinerary.
  ///
  /// In en, this message translates to:
  /// **'Trips'**
  String get navItinerary;

  /// No description provided for @navTravelTools.
  ///
  /// In en, this message translates to:
  /// **'Tools'**
  String get navTravelTools;

  /// No description provided for @navProfile.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get navProfile;

  /// No description provided for @itineraryTitle.
  ///
  /// In en, this message translates to:
  /// **'My Trips'**
  String get itineraryTitle;

  /// No description provided for @itineraryEmptyTitle.
  ///
  /// In en, this message translates to:
  /// **'No trips yet'**
  String get itineraryEmptyTitle;

  /// No description provided for @itineraryEmptyBody.
  ///
  /// In en, this message translates to:
  /// **'Your saved and planned China journeys will appear here.'**
  String get itineraryEmptyBody;

  /// No description provided for @travelToolsTitle.
  ///
  /// In en, this message translates to:
  /// **'Travel Tools'**
  String get travelToolsTitle;

  /// No description provided for @travelToolsIntro.
  ///
  /// In en, this message translates to:
  /// **'Practical essentials for entering China and travelling with confidence.'**
  String get travelToolsIntro;

  /// No description provided for @toolVisaTitle.
  ///
  /// In en, this message translates to:
  /// **'Visa & Entry'**
  String get toolVisaTitle;

  /// No description provided for @toolVisaSummary.
  ///
  /// In en, this message translates to:
  /// **'Documents and arrival preparation'**
  String get toolVisaSummary;

  /// No description provided for @toolVisaDetail.
  ///
  /// In en, this message translates to:
  /// **'Entry policies depend on your nationality, travel document, and route. Check the latest requirements with the Chinese embassy or consulate before booking, and keep digital and printed copies of your passport, visa, accommodation, and return itinerary.'**
  String get toolVisaDetail;

  /// No description provided for @toolPaymentTitle.
  ///
  /// In en, this message translates to:
  /// **'Payments'**
  String get toolPaymentTitle;

  /// No description provided for @toolPaymentSummary.
  ///
  /// In en, this message translates to:
  /// **'Cards, mobile payment, and emergency cash'**
  String get toolPaymentSummary;

  /// No description provided for @toolPaymentDetail.
  ///
  /// In en, this message translates to:
  /// **'Confirm overseas payment support with your bank before departure. Prepare at least one international card and a small amount of cash, and complete any mobile payment setup before you need it.'**
  String get toolPaymentDetail;

  /// No description provided for @toolTransportTitle.
  ///
  /// In en, this message translates to:
  /// **'Trains & Local Transport'**
  String get toolTransportTitle;

  /// No description provided for @toolTransportSummary.
  ///
  /// In en, this message translates to:
  /// **'Tickets, stations, and passport checks'**
  String get toolTransportSummary;

  /// No description provided for @toolTransportDetail.
  ///
  /// In en, this message translates to:
  /// **'High-speed rail tickets are normally linked to the passport used for booking. Arrive early for identity checks, verify the exact station name, and keep the original travel document with you.'**
  String get toolTransportDetail;

  /// No description provided for @toolInternetTitle.
  ///
  /// In en, this message translates to:
  /// **'Internet & SIM'**
  String get toolInternetTitle;

  /// No description provided for @toolInternetSummary.
  ///
  /// In en, this message translates to:
  /// **'Roaming, eSIM, and connectivity'**
  String get toolInternetSummary;

  /// No description provided for @toolInternetDetail.
  ///
  /// In en, this message translates to:
  /// **'Arrange international roaming, an eSIM, or a local SIM before or soon after arrival. Download essential travel information and offline translations in advance in case connectivity is limited.'**
  String get toolInternetDetail;

  /// No description provided for @profileTitle.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get profileTitle;

  /// No description provided for @profilePreferences.
  ///
  /// In en, this message translates to:
  /// **'Preferences'**
  String get profilePreferences;

  /// No description provided for @profileLanguage.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get profileLanguage;

  /// No description provided for @profileMoreAssistance.
  ///
  /// In en, this message translates to:
  /// **'More Assistance'**
  String get profileMoreAssistance;

  /// No description provided for @profileAbout.
  ///
  /// In en, this message translates to:
  /// **'About'**
  String get profileAbout;

  /// No description provided for @profileAppVersion.
  ///
  /// In en, this message translates to:
  /// **'App Version'**
  String get profileAppVersion;

  /// No description provided for @profileLicenses.
  ///
  /// In en, this message translates to:
  /// **'Open-source Licenses'**
  String get profileLicenses;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['de', 'en', 'fr', 'zh'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'de':
      return AppLocalizationsDe();
    case 'en':
      return AppLocalizationsEn();
    case 'fr':
      return AppLocalizationsFr();
    case 'zh':
      return AppLocalizationsZh();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
