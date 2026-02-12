<?php
/**
 * Predictions Redirects - Week 1 Foundation
 * Handles legacy URL redirects to unified structure
 */

$redirect_map = [
  '/findstocks/portfolio2/leaderboard.html' => '/predictions/leaderboard.html',
  '/findstocks/portfolio2/dashboard.html' => '/predictions/dashboard.html',
  '/live-monitor/sports-betting.html' => '/predictions/sports.html',
  '/findstocks/portfolio2/picks.html' => '/predictions/dashboard.html',
  '/findstocks/portfolio2/horizon-picks.html' => '/predictions/dashboard.html'
];

foreach ($redirect_map as $old => $new) {
  if ($_SERVER['REQUEST_URI'] === $old) {
    header('Location: ' . $new, true, 301);
    exit;
  }
}

// If no redirect, serve index
include 'dashboard.html';
?>