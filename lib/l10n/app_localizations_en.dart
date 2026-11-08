// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Meditour';

  @override
  String get appSubtitle => 'Your Gateway to China';

  @override
  String get tagline => 'From Europe to China';

  @override
  String get taglineSubtitle =>
      '5,000 years of civilization, waiting for you to explore';

  @override
  String get searchHint => 'Search destinations, attractions, food…';

  @override
  String get searchComingSoon => 'Search will be available in the next version';

  @override
  String get heroTitle =>
      'Climb the Great Wall · Explore the Forbidden City · Taste Hot Pot';

  @override
  String get heroSubtitle =>
      'Visa assistance · Transport booking · Custom itineraries — all in one place';

  @override
  String get chipVisa => 'Visa Assistance';

  @override
  String get chipTransport => 'Trains & Flights';

  @override
  String get chipHotel => 'Hotel Booking';

  @override
  String get chipItinerary => 'Custom Itinerary';

  @override
  String get chipComingSoon => 'will be available in the next version';

  @override
  String get sectionDestinations => 'Popular Destinations';

  @override
  String get sectionDestinationsSub => '4 cities selected';

  @override
  String get sectionTips => 'Travel Tips';

  @override
  String get tipPayment =>
      'China is fully cashless — exchange a small amount at the airport for emergencies; major hotels and duty-free shops accept foreign cards';

  @override
  String get tipSim =>
      'Get a Chinese SIM card or eSIM before departure for easy scanning, translation, and navigation';

  @override
  String get medicalEntryTitle => 'Health Concierge';

  @override
  String get medicalEntrySub =>
      'Need medical care during your trip? We\'ve got you covered';

  @override
  String get footerText => 'Meditour · Making every China journey worry-free';

  @override
  String get homeAppBarTitle => 'Discover China';

  @override
  String get medicalListTitle => 'Health Concierge';

  @override
  String get medicalListInfo =>
      'If you have medical needs during your trip, we can connect you with premium healthcare resources. No worries if not — come back anytime to continue exploring.';

  @override
  String get destinationNotFound => 'Destination not found';

  @override
  String get serviceNotFound => 'Service not found';

  @override
  String get sectionImpression => 'City Impression';

  @override
  String get sectionExperiences => 'Must-Try Experiences';

  @override
  String get sectionTravelTips => 'Travel Tips';

  @override
  String get sectionIntro => 'Service Overview';

  @override
  String get sectionHighlights => 'Highlights';

  @override
  String get sectionProcess => 'Process';

  @override
  String get statBestSeason => 'Best Season';

  @override
  String get statSuggestDays => 'Suggested Days';

  @override
  String get statBasePrice => 'Base Price';

  @override
  String get statDuration => 'Duration';

  @override
  String get statCompanion => 'Companion';

  @override
  String get btnItinerary => 'Inquire About Itinerary';

  @override
  String get btnBookConsult => 'Book Consultation';

  @override
  String get btnSubmit => 'Submit Booking';

  @override
  String get btnBackHome => 'Back to Home';

  @override
  String get btnViewService => 'View Service Details';

  @override
  String get itineraryComingSoon =>
      'Custom itinerary consultation will be available in the next version';

  @override
  String get bookingSuccess => 'Booking Submitted Successfully!';

  @override
  String get bookingSuccessDesc =>
      'Thank you for your trust! Your medical concierge will contact you within 24 hours via your provided contact method.';

  @override
  String get bookingNo => 'Booking No.';

  @override
  String get bookingNote =>
      '🔒 Your information is used solely for this booking. A medical concierge will contact you within 24 hours.';

  @override
  String get formName => 'Name';

  @override
  String get formNameError => 'Please enter your name';

  @override
  String get formContact => 'Contact (Email / Phone)';

  @override
  String get formContactHint => 'For concierge to confirm your itinerary';

  @override
  String get formContactError => 'Please enter a valid contact';

  @override
  String get formDate => 'Preferred Date';

  @override
  String get formDateHint => 'Select a date';

  @override
  String get formNote => 'Condition / Needs';

  @override
  String get formNoteHint => 'Briefly describe your situation (optional)';

  @override
  String daysTreatment(int days) {
    return '$days days treatment';
  }

  @override
  String get hospitalLabel => 'Hospital';

  @override
  String get priceLabel => 'Base price';

  @override
  String get durationLabel => 'Duration';

  @override
  String startingFrom(String price) {
    return 'from $price';
  }

  @override
  String get level3A => 'Grade 3A';

  @override
  String get navDiscover => 'Discover';

  @override
  String get navItinerary => 'Trips';

  @override
  String get navTravelTools => 'Tools';

  @override
  String get navProfile => 'Profile';

  @override
  String get itineraryTitle => 'My Trips';

  @override
  String get itineraryEmptyTitle => 'No trips yet';

  @override
  String get itineraryEmptyBody =>
      'Your saved and planned China journeys will appear here.';

  @override
  String get travelToolsTitle => 'Travel Tools';

  @override
  String get travelToolsIntro =>
      'Practical essentials for entering China and travelling with confidence.';

  @override
  String get toolVisaTitle => 'Visa & Entry';

  @override
  String get toolVisaSummary => 'Documents and arrival preparation';

  @override
  String get toolVisaDetail =>
      'Entry policies depend on your nationality, travel document, and route. Check the latest requirements with the Chinese embassy or consulate before booking, and keep digital and printed copies of your passport, visa, accommodation, and return itinerary.';

  @override
  String get toolPaymentTitle => 'Payments';

  @override
  String get toolPaymentSummary => 'Cards, mobile payment, and emergency cash';

  @override
  String get toolPaymentDetail =>
      'Confirm overseas payment support with your bank before departure. Prepare at least one international card and a small amount of cash, and complete any mobile payment setup before you need it.';

  @override
  String get toolTransportTitle => 'Trains & Local Transport';

  @override
  String get toolTransportSummary => 'Tickets, stations, and passport checks';

  @override
  String get toolTransportDetail =>
      'High-speed rail tickets are normally linked to the passport used for booking. Arrive early for identity checks, verify the exact station name, and keep the original travel document with you.';

  @override
  String get toolInternetTitle => 'Internet & SIM';

  @override
  String get toolInternetSummary => 'Roaming, eSIM, and connectivity';

  @override
  String get toolInternetDetail =>
      'Arrange international roaming, an eSIM, or a local SIM before or soon after arrival. Download essential travel information and offline translations in advance in case connectivity is limited.';

  @override
  String get profileTitle => 'Profile';

  @override
  String get profilePreferences => 'Preferences';

  @override
  String get profileLanguage => 'Language';

  @override
  String get profileMoreAssistance => 'More Assistance';

  @override
  String get profileAbout => 'About';

  @override
  String get profileAppVersion => 'App Version';

  @override
  String get profileLicenses => 'Open-source Licenses';

  @override
  String get profileBookings => 'My Bookings';

  @override
  String get profileBookingsSub => 'View your medical service orders';

  @override
  String get bookingsLoginBody =>
      'Log in to view your bookings and appointment details.';

  @override
  String get bookingsEmptyTitle => 'No bookings yet';

  @override
  String get bookingsEmptyBody =>
      'Your submitted medical service bookings will appear here.';

  @override
  String get bookingsLoadFailed => 'Failed to load bookings';

  @override
  String get bookingsAppointmentDate => 'Appointment date';

  @override
  String get bookingsStatusPending => 'Pending';

  @override
  String get bookingsStatusConfirmed => 'Confirmed';

  @override
  String get bookingsStatusCompleted => 'Completed';

  @override
  String get bookingsStatusCancelled => 'Cancelled';

  @override
  String get bookingsStatusUnknown => 'Unknown status';

  @override
  String get bookingsCreatedAt => 'Booked on';

  @override
  String get bookingsCancel => 'Cancel booking';

  @override
  String get bookingsCancelTitle => 'Cancel booking';

  @override
  String get bookingsCancelBody =>
      'This cannot be undone. Are you sure you want to cancel this booking?';

  @override
  String get bookingsCancelConfirm => 'Cancel booking';

  @override
  String get bookingsCancelDismiss => 'Keep';

  @override
  String get bookingsCancelSuccess => 'Booking cancelled';

  @override
  String get bookingsCancelNotFound =>
      'This booking was not found or you no longer have access to it';

  @override
  String get bookingsCancelConflict =>
      'This booking can no longer be cancelled';

  @override
  String get destinationSearchTitle => 'Search Destinations';

  @override
  String get destinationFilterAll => 'All';

  @override
  String get destinationFilterFavorites => 'Saved';

  @override
  String get clearSearch => 'Clear search';

  @override
  String get searchNoResultsTitle => 'No destinations found';

  @override
  String get searchNoResultsBody =>
      'Try another city, attraction, or food keyword.';

  @override
  String get favoriteEmptyTitle => 'No saved destinations';

  @override
  String get favoriteEmptyBody =>
      'Tap the heart on a destination to keep it here.';

  @override
  String get addToFavorites => 'Save destination';

  @override
  String get removeFromFavorites => 'Remove from saved';

  @override
  String get itineraryCreateTitle => 'Create Trip';

  @override
  String get itineraryEditTitle => 'Edit Trip';

  @override
  String get itineraryNotFound => 'Trip not found';

  @override
  String get itineraryNewButton => 'New Trip';

  @override
  String get itineraryNameLabel => 'Trip name';

  @override
  String get itineraryNameHint => 'e.g. Spring in China';

  @override
  String get itineraryNameError => 'Enter a trip name';

  @override
  String get itineraryDestinationsLabel => 'Destinations';

  @override
  String get itineraryDestinationsError => 'Select at least one destination';

  @override
  String get itineraryDatesLabel => 'Travel dates';

  @override
  String get itineraryDatesHint => 'Select start and end dates';

  @override
  String get itineraryDatesError => 'Select your travel dates';

  @override
  String get itineraryDayPlanLabel => 'Day-by-day plan';

  @override
  String get itineraryDayPlanHint =>
      'Select travel dates first, then plan each day.';

  @override
  String itineraryDayLabel(int day) {
    return 'Day $day';
  }

  @override
  String get itineraryDayNotesHint => 'Notes for this day';

  @override
  String get itineraryAddPlace => 'Add place';

  @override
  String get itinerarySelectPlace => 'Select a place';

  @override
  String get itineraryNoPlacesInDay => 'No places planned yet';

  @override
  String get itineraryMoveUp => 'Move up';

  @override
  String get itineraryMoveDown => 'Move down';

  @override
  String get itineraryRemovePlace => 'Remove place';

  @override
  String get itineraryNotesLabel => 'Notes';

  @override
  String get itineraryNotesHint =>
      'Transport, hotels, places to visit, or other plans';

  @override
  String get itinerarySave => 'Save Trip';

  @override
  String get itineraryActions => 'Trip actions';

  @override
  String get itineraryEditAction => 'Edit';

  @override
  String get itineraryDeleteAction => 'Delete';

  @override
  String get itineraryDeleteTitle => 'Delete this trip?';

  @override
  String get itineraryDeleteBody =>
      'This saved trip will be removed from this device.';

  @override
  String get cancel => 'Cancel';

  @override
  String itineraryDays(int days) {
    return '$days days';
  }

  @override
  String get addToTripCreateNew => 'Create a new trip and add';

  @override
  String get addToTripAdded => 'Added to your trip';

  @override
  String get profileAccount => 'Account';

  @override
  String get loginTitle => 'Log In';

  @override
  String get registerTitle => 'Create Account';

  @override
  String get emailLabel => 'Email';

  @override
  String get emailError => 'Please enter a valid email address';

  @override
  String get passwordLabel => 'Password';

  @override
  String get passwordError => 'Password must be at least 6 characters';

  @override
  String get passwordConfirmLabel => 'Confirm Password';

  @override
  String get passwordMismatch => 'Passwords do not match';

  @override
  String get fullNameLabel => 'Full Name (optional)';

  @override
  String get loginButton => 'Log In';

  @override
  String get registerButton => 'Create Account';

  @override
  String get loginSwitchToRegister => 'No account yet? Create one';

  @override
  String get registerSwitchToLogin => 'Already have an account? Log in';

  @override
  String get logout => 'Log Out';

  @override
  String get loginEntrySub => 'Log in to book medical services';

  @override
  String get loginRequiredTitle => 'Log in required';

  @override
  String get loginRequiredBody =>
      'Please log in or create an account to submit your booking.';

  @override
  String get goLogin => 'Log In';

  @override
  String get formPhone => 'Phone';

  @override
  String get formPhoneError => 'Please enter a valid phone number';

  @override
  String get formEmail => 'Email';

  @override
  String get formEmailError => 'Please enter a valid email address';

  @override
  String get formDateError => 'Please select a preferred date';

  @override
  String get extrasTitle => 'Additional Services';

  @override
  String get needTranslator => 'Translator companion';

  @override
  String get needAccommodation => 'Accommodation arrangement';

  @override
  String get needPickup => 'Airport pickup';

  @override
  String get bookingTotal => 'Total';

  @override
  String get bookingPackageNotFound =>
      'This service is no longer available. Please go back and pick another one.';

  @override
  String get errorNetwork =>
      'Network unavailable. Please check your connection and try again.';

  @override
  String get errorUnauthorized => 'Login expired. Please log in again.';

  @override
  String get errorInvalidCredentials => 'Incorrect email or password.';

  @override
  String get errorServer => 'Server is busy. Please try again later.';

  @override
  String get errorUnknown => 'Something went wrong. Please try again.';

  @override
  String get errorRequest =>
      'We couldn\'t complete this request. Please check your details and try again.';

  @override
  String get medicalOfflineHint =>
      'Temporarily unable to reach the server — showing sample data.';

  @override
  String get medicalLoadFailed => 'Failed to load';

  @override
  String get medicalEmptyTitle => 'No services yet';

  @override
  String get medicalEmptyBody =>
      'No medical services are available right now. Please try again later.';

  @override
  String get retry => 'Retry';
}
