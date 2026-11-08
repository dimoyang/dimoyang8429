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
  /// **'🔒 Your information is used solely for this booking. A medical concierge will contact you within 24 hours.'**
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
  /// **'from {price}'**
  String startingFrom(String price);

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

  /// No description provided for @profileBookings.
  ///
  /// In en, this message translates to:
  /// **'My Bookings'**
  String get profileBookings;

  /// No description provided for @profileBookingsSub.
  ///
  /// In en, this message translates to:
  /// **'View your medical service orders'**
  String get profileBookingsSub;

  /// No description provided for @bookingsLoginBody.
  ///
  /// In en, this message translates to:
  /// **'Log in to view your bookings and appointment details.'**
  String get bookingsLoginBody;

  /// No description provided for @bookingsEmptyTitle.
  ///
  /// In en, this message translates to:
  /// **'No bookings yet'**
  String get bookingsEmptyTitle;

  /// No description provided for @bookingsEmptyBody.
  ///
  /// In en, this message translates to:
  /// **'Your submitted medical service bookings will appear here.'**
  String get bookingsEmptyBody;

  /// No description provided for @bookingsLoadFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed to load bookings'**
  String get bookingsLoadFailed;

  /// No description provided for @bookingsAppointmentDate.
  ///
  /// In en, this message translates to:
  /// **'Appointment date'**
  String get bookingsAppointmentDate;

  /// No description provided for @bookingsStatusPending.
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get bookingsStatusPending;

  /// No description provided for @bookingsStatusConfirmed.
  ///
  /// In en, this message translates to:
  /// **'Confirmed'**
  String get bookingsStatusConfirmed;

  /// No description provided for @bookingsStatusCompleted.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get bookingsStatusCompleted;

  /// No description provided for @bookingsStatusCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get bookingsStatusCancelled;

  /// No description provided for @bookingsStatusUnknown.
  ///
  /// In en, this message translates to:
  /// **'Unknown status'**
  String get bookingsStatusUnknown;

  /// No description provided for @bookingsCreatedAt.
  ///
  /// In en, this message translates to:
  /// **'Booked on'**
  String get bookingsCreatedAt;

  /// No description provided for @bookingsCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel booking'**
  String get bookingsCancel;

  /// No description provided for @bookingsCancelTitle.
  ///
  /// In en, this message translates to:
  /// **'Cancel booking'**
  String get bookingsCancelTitle;

  /// No description provided for @bookingsCancelBody.
  ///
  /// In en, this message translates to:
  /// **'This cannot be undone. Are you sure you want to cancel this booking?'**
  String get bookingsCancelBody;

  /// No description provided for @bookingsCancelConfirm.
  ///
  /// In en, this message translates to:
  /// **'Cancel booking'**
  String get bookingsCancelConfirm;

  /// No description provided for @bookingsCancelDismiss.
  ///
  /// In en, this message translates to:
  /// **'Keep'**
  String get bookingsCancelDismiss;

  /// No description provided for @bookingsCancelSuccess.
  ///
  /// In en, this message translates to:
  /// **'Booking cancelled'**
  String get bookingsCancelSuccess;

  /// No description provided for @bookingsCancelNotFound.
  ///
  /// In en, this message translates to:
  /// **'This booking was not found or you no longer have access to it'**
  String get bookingsCancelNotFound;

  /// No description provided for @bookingsCancelConflict.
  ///
  /// In en, this message translates to:
  /// **'This booking can no longer be cancelled'**
  String get bookingsCancelConflict;

  /// No description provided for @destinationSearchTitle.
  ///
  /// In en, this message translates to:
  /// **'Search Destinations'**
  String get destinationSearchTitle;

  /// No description provided for @destinationFilterAll.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get destinationFilterAll;

  /// No description provided for @destinationFilterFavorites.
  ///
  /// In en, this message translates to:
  /// **'Saved'**
  String get destinationFilterFavorites;

  /// No description provided for @clearSearch.
  ///
  /// In en, this message translates to:
  /// **'Clear search'**
  String get clearSearch;

  /// No description provided for @searchNoResultsTitle.
  ///
  /// In en, this message translates to:
  /// **'No destinations found'**
  String get searchNoResultsTitle;

  /// No description provided for @searchNoResultsBody.
  ///
  /// In en, this message translates to:
  /// **'Try another city, attraction, or food keyword.'**
  String get searchNoResultsBody;

  /// No description provided for @favoriteEmptyTitle.
  ///
  /// In en, this message translates to:
  /// **'No saved destinations'**
  String get favoriteEmptyTitle;

  /// No description provided for @favoriteEmptyBody.
  ///
  /// In en, this message translates to:
  /// **'Tap the heart on a destination to keep it here.'**
  String get favoriteEmptyBody;

  /// No description provided for @addToFavorites.
  ///
  /// In en, this message translates to:
  /// **'Save destination'**
  String get addToFavorites;

  /// No description provided for @removeFromFavorites.
  ///
  /// In en, this message translates to:
  /// **'Remove from saved'**
  String get removeFromFavorites;

  /// No description provided for @itineraryCreateTitle.
  ///
  /// In en, this message translates to:
  /// **'Create Trip'**
  String get itineraryCreateTitle;

  /// No description provided for @itineraryEditTitle.
  ///
  /// In en, this message translates to:
  /// **'Edit Trip'**
  String get itineraryEditTitle;

  /// No description provided for @itineraryNotFound.
  ///
  /// In en, this message translates to:
  /// **'Trip not found'**
  String get itineraryNotFound;

  /// No description provided for @itineraryNewButton.
  ///
  /// In en, this message translates to:
  /// **'New Trip'**
  String get itineraryNewButton;

  /// No description provided for @itineraryNameLabel.
  ///
  /// In en, this message translates to:
  /// **'Trip name'**
  String get itineraryNameLabel;

  /// No description provided for @itineraryNameHint.
  ///
  /// In en, this message translates to:
  /// **'e.g. Spring in China'**
  String get itineraryNameHint;

  /// No description provided for @itineraryNameError.
  ///
  /// In en, this message translates to:
  /// **'Enter a trip name'**
  String get itineraryNameError;

  /// No description provided for @itineraryDestinationsLabel.
  ///
  /// In en, this message translates to:
  /// **'Destinations'**
  String get itineraryDestinationsLabel;

  /// No description provided for @itineraryDestinationsError.
  ///
  /// In en, this message translates to:
  /// **'Select at least one destination'**
  String get itineraryDestinationsError;

  /// No description provided for @itineraryDatesLabel.
  ///
  /// In en, this message translates to:
  /// **'Travel dates'**
  String get itineraryDatesLabel;

  /// No description provided for @itineraryDatesHint.
  ///
  /// In en, this message translates to:
  /// **'Select start and end dates'**
  String get itineraryDatesHint;

  /// No description provided for @itineraryDatesError.
  ///
  /// In en, this message translates to:
  /// **'Select your travel dates'**
  String get itineraryDatesError;

  /// No description provided for @itineraryDayPlanLabel.
  ///
  /// In en, this message translates to:
  /// **'Day-by-day plan'**
  String get itineraryDayPlanLabel;

  /// No description provided for @itineraryDayPlanHint.
  ///
  /// In en, this message translates to:
  /// **'Select travel dates first, then plan each day.'**
  String get itineraryDayPlanHint;

  /// No description provided for @itineraryDayLabel.
  ///
  /// In en, this message translates to:
  /// **'Day {day}'**
  String itineraryDayLabel(int day);

  /// No description provided for @itineraryDayNotesHint.
  ///
  /// In en, this message translates to:
  /// **'Notes for this day'**
  String get itineraryDayNotesHint;

  /// No description provided for @itineraryAddPlace.
  ///
  /// In en, this message translates to:
  /// **'Add place'**
  String get itineraryAddPlace;

  /// No description provided for @itinerarySelectPlace.
  ///
  /// In en, this message translates to:
  /// **'Select a place'**
  String get itinerarySelectPlace;

  /// No description provided for @itineraryNoPlacesInDay.
  ///
  /// In en, this message translates to:
  /// **'No places planned yet'**
  String get itineraryNoPlacesInDay;

  /// No description provided for @itineraryMoveUp.
  ///
  /// In en, this message translates to:
  /// **'Move up'**
  String get itineraryMoveUp;

  /// No description provided for @itineraryMoveDown.
  ///
  /// In en, this message translates to:
  /// **'Move down'**
  String get itineraryMoveDown;

  /// No description provided for @itineraryRemovePlace.
  ///
  /// In en, this message translates to:
  /// **'Remove place'**
  String get itineraryRemovePlace;

  /// No description provided for @itineraryNotesLabel.
  ///
  /// In en, this message translates to:
  /// **'Notes'**
  String get itineraryNotesLabel;

  /// No description provided for @itineraryNotesHint.
  ///
  /// In en, this message translates to:
  /// **'Transport, hotels, places to visit, or other plans'**
  String get itineraryNotesHint;

  /// No description provided for @itinerarySave.
  ///
  /// In en, this message translates to:
  /// **'Save Trip'**
  String get itinerarySave;

  /// No description provided for @itineraryActions.
  ///
  /// In en, this message translates to:
  /// **'Trip actions'**
  String get itineraryActions;

  /// No description provided for @itineraryEditAction.
  ///
  /// In en, this message translates to:
  /// **'Edit'**
  String get itineraryEditAction;

  /// No description provided for @itineraryDeleteAction.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get itineraryDeleteAction;

  /// No description provided for @itineraryDeleteTitle.
  ///
  /// In en, this message translates to:
  /// **'Delete this trip?'**
  String get itineraryDeleteTitle;

  /// No description provided for @itineraryDeleteBody.
  ///
  /// In en, this message translates to:
  /// **'This saved trip will be removed from this device.'**
  String get itineraryDeleteBody;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @itineraryDays.
  ///
  /// In en, this message translates to:
  /// **'{days} days'**
  String itineraryDays(int days);

  /// No description provided for @addToTripCreateNew.
  ///
  /// In en, this message translates to:
  /// **'Create a new trip and add'**
  String get addToTripCreateNew;

  /// No description provided for @addToTripAdded.
  ///
  /// In en, this message translates to:
  /// **'Added to your trip'**
  String get addToTripAdded;

  /// No description provided for @profileAccount.
  ///
  /// In en, this message translates to:
  /// **'Account'**
  String get profileAccount;

  /// No description provided for @loginTitle.
  ///
  /// In en, this message translates to:
  /// **'Log In'**
  String get loginTitle;

  /// No description provided for @registerTitle.
  ///
  /// In en, this message translates to:
  /// **'Create Account'**
  String get registerTitle;

  /// No description provided for @emailLabel.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get emailLabel;

  /// No description provided for @emailError.
  ///
  /// In en, this message translates to:
  /// **'Please enter a valid email address'**
  String get emailError;

  /// No description provided for @passwordLabel.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get passwordLabel;

  /// No description provided for @passwordError.
  ///
  /// In en, this message translates to:
  /// **'Password must be at least 6 characters'**
  String get passwordError;

  /// No description provided for @passwordConfirmLabel.
  ///
  /// In en, this message translates to:
  /// **'Confirm Password'**
  String get passwordConfirmLabel;

  /// No description provided for @passwordMismatch.
  ///
  /// In en, this message translates to:
  /// **'Passwords do not match'**
  String get passwordMismatch;

  /// No description provided for @fullNameLabel.
  ///
  /// In en, this message translates to:
  /// **'Full Name (optional)'**
  String get fullNameLabel;

  /// No description provided for @loginButton.
  ///
  /// In en, this message translates to:
  /// **'Log In'**
  String get loginButton;

  /// No description provided for @registerButton.
  ///
  /// In en, this message translates to:
  /// **'Create Account'**
  String get registerButton;

  /// No description provided for @loginSwitchToRegister.
  ///
  /// In en, this message translates to:
  /// **'No account yet? Create one'**
  String get loginSwitchToRegister;

  /// No description provided for @registerSwitchToLogin.
  ///
  /// In en, this message translates to:
  /// **'Already have an account? Log in'**
  String get registerSwitchToLogin;

  /// No description provided for @logout.
  ///
  /// In en, this message translates to:
  /// **'Log Out'**
  String get logout;

  /// No description provided for @loginEntrySub.
  ///
  /// In en, this message translates to:
  /// **'Log in to book medical services'**
  String get loginEntrySub;

  /// No description provided for @loginRequiredTitle.
  ///
  /// In en, this message translates to:
  /// **'Log in required'**
  String get loginRequiredTitle;

  /// No description provided for @loginRequiredBody.
  ///
  /// In en, this message translates to:
  /// **'Please log in or create an account to submit your booking.'**
  String get loginRequiredBody;

  /// No description provided for @goLogin.
  ///
  /// In en, this message translates to:
  /// **'Log In'**
  String get goLogin;

  /// No description provided for @formPhone.
  ///
  /// In en, this message translates to:
  /// **'Phone'**
  String get formPhone;

  /// No description provided for @formPhoneError.
  ///
  /// In en, this message translates to:
  /// **'Please enter a valid phone number'**
  String get formPhoneError;

  /// No description provided for @formEmail.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get formEmail;

  /// No description provided for @formEmailError.
  ///
  /// In en, this message translates to:
  /// **'Please enter a valid email address'**
  String get formEmailError;

  /// No description provided for @formDateError.
  ///
  /// In en, this message translates to:
  /// **'Please select a preferred date'**
  String get formDateError;

  /// No description provided for @extrasTitle.
  ///
  /// In en, this message translates to:
  /// **'Additional Services'**
  String get extrasTitle;

  /// No description provided for @needTranslator.
  ///
  /// In en, this message translates to:
  /// **'Translator companion'**
  String get needTranslator;

  /// No description provided for @needAccommodation.
  ///
  /// In en, this message translates to:
  /// **'Accommodation arrangement'**
  String get needAccommodation;

  /// No description provided for @needPickup.
  ///
  /// In en, this message translates to:
  /// **'Airport pickup'**
  String get needPickup;

  /// No description provided for @bookingTotal.
  ///
  /// In en, this message translates to:
  /// **'Total'**
  String get bookingTotal;

  /// No description provided for @bookingPackageNotFound.
  ///
  /// In en, this message translates to:
  /// **'This service is no longer available. Please go back and pick another one.'**
  String get bookingPackageNotFound;

  /// No description provided for @errorNetwork.
  ///
  /// In en, this message translates to:
  /// **'Network unavailable. Please check your connection and try again.'**
  String get errorNetwork;

  /// No description provided for @errorUnauthorized.
  ///
  /// In en, this message translates to:
  /// **'Login expired. Please log in again.'**
  String get errorUnauthorized;

  /// No description provided for @errorInvalidCredentials.
  ///
  /// In en, this message translates to:
  /// **'Incorrect email or password.'**
  String get errorInvalidCredentials;

  /// No description provided for @errorServer.
  ///
  /// In en, this message translates to:
  /// **'Server is busy. Please try again later.'**
  String get errorServer;

  /// No description provided for @errorUnknown.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong. Please try again.'**
  String get errorUnknown;

  /// No description provided for @errorRequest.
  ///
  /// In en, this message translates to:
  /// **'We couldn\'t complete this request. Please check your details and try again.'**
  String get errorRequest;

  /// No description provided for @medicalOfflineHint.
  ///
  /// In en, this message translates to:
  /// **'Temporarily unable to reach the server — showing sample data.'**
  String get medicalOfflineHint;

  /// No description provided for @medicalLoadFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed to load'**
  String get medicalLoadFailed;

  /// No description provided for @medicalEmptyTitle.
  ///
  /// In en, this message translates to:
  /// **'No services yet'**
  String get medicalEmptyTitle;

  /// No description provided for @medicalEmptyBody.
  ///
  /// In en, this message translates to:
  /// **'No medical services are available right now. Please try again later.'**
  String get medicalEmptyBody;

  /// No description provided for @retry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get retry;
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
