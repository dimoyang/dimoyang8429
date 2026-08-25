import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/presentation/screens/booking_screen.dart';
import 'package:meditour_app/presentation/screens/destination_detail_screen.dart';
import 'package:meditour_app/presentation/screens/destination_search_screen.dart';
import 'package:meditour_app/presentation/screens/home_screen.dart';
import 'package:meditour_app/presentation/screens/itinerary_screen.dart';
import 'package:meditour_app/presentation/screens/main_shell_screen.dart';
import 'package:meditour_app/presentation/screens/medical_list_screen.dart';
import 'package:meditour_app/presentation/screens/profile_screen.dart';
import 'package:meditour_app/presentation/screens/service_detail_screen.dart';
import 'package:meditour_app/presentation/screens/travel_tools_screen.dart';

/// 应用路由配置
class AppRouter {
  AppRouter._();

  static final _rootNavigatorKey =
      GlobalKey<NavigatorState>(debugLabel: 'root');

  static final GoRouter router = GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/',
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) => MainShellScreen(
          navigationShell: navigationShell,
        ),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/',
                name: 'home',
                builder: (context, state) => const HomeScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/itinerary',
                name: 'itinerary',
                builder: (context, state) => const ItineraryScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/travel-tools',
                name: 'travelTools',
                builder: (context, state) => const TravelToolsScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/profile',
                name: 'profile',
                builder: (context, state) => const ProfileScreen(),
              ),
            ],
          ),
        ],
      ),
      GoRoute(
        path: '/search',
        name: 'destinationSearch',
        builder: (context, state) => const DestinationSearchScreen(),
      ),
      GoRoute(
        path: '/destinations/:id',
        name: 'destinationDetail',
        builder: (context, state) => DestinationDetailScreen(
          destinationId: state.pathParameters['id'] ?? '',
        ),
      ),
      GoRoute(
        path: '/medical',
        name: 'medical',
        builder: (context, state) => const MedicalListScreen(),
        routes: [
          GoRoute(
            path: 'services/:id',
            name: 'serviceDetail',
            builder: (context, state) => ServiceDetailScreen(
              serviceId: state.pathParameters['id'] ?? '',
            ),
            routes: [
              GoRoute(
                path: 'booking',
                name: 'booking',
                builder: (context, state) => BookingScreen(
                  serviceId: state.pathParameters['id'] ?? '',
                ),
              ),
            ],
          ),
        ],
      ),
    ],
  );
}
