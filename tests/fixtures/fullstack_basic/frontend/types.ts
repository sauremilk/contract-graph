// TypeScript interfaces for API responses — INTENTIONALLY DRIFTED from backend

export interface MatchResponse {
  id: string;
  playerName: string;      // camelCase vs snake_case
  score: number;
  durationSeconds: number;
  mapName: string;
  isRanked: boolean;
  createdAt: string;        // string vs datetime
  kills: number;
  deaths: number;
  assists: number;
  placement: number;
  // match_mode MISSING — intentional drift
}

export interface PlayerStats {
  playerId: string;
  displayName: string;
  totalMatches: number;
  winRate: number;
  averageKills: number;
  kdRatio: number;
  lastPlayed?: string;       // optional vs Optional
  rank: string;
  level: number;
  favoriteWeapon: string;    // extra field — not in backend
}

// PHANTOM type — no matching backend model
export interface TournamentBracket {
  bracketId: string;
  round: number;
  teams: string[];
  winner?: string;
}

export interface SessionConfig {
  theme: string;
  language: string;
  autoRecord: boolean;
  overlayOpacity: number;
  notificationSound: boolean;
  keybindToggle: string;
}
