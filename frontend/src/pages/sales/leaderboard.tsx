/**
 * Sales Leaderboard Page
 * Real-time team rankings and achievements
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Trophy,
  Medal,
  Crown,
  Flame,
  TrendingUp,
  Users,
  Target,
  Award,
  Star,
  Zap,
} from "lucide-react";
import { getLeaderboard, getLeaderboardStats, getAchievements } from "@/api/elite-sales";

export function LeaderboardPage() {
  const salespersonId = 1; // TODO: Get from auth context
  const [period, setPeriod] = useState<"TODAY" | "THIS_WEEK" | "THIS_MONTH">("TODAY");

  // Fetch leaderboard
  const { data: leaderboardData, isLoading } = useQuery({
    queryKey: ["leaderboard", period],
    queryFn: () => getLeaderboard(period),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch stats
  const { data: statsData } = useQuery({
    queryKey: ["leaderboard-stats"],
    queryFn: getLeaderboardStats,
  });

  // Fetch current user achievements
  const { data: achievementsData } = useQuery({
    queryKey: ["achievements", salespersonId],
    queryFn: () => getAchievements(salespersonId),
  });

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <Crown className="h-6 w-6 text-yellow-500" />;
      case 2:
        return <Medal className="h-6 w-6 text-gray-400" />;
      case 3:
        return <Medal className="h-6 w-6 text-orange-400" />;
      default:
        return null;
    }
  };

  const getRankBg = (rank: number) => {
    switch (rank) {
      case 1:
        return "bg-gradient-to-r from-yellow-500/20 to-yellow-600/10 border-yellow-500/30";
      case 2:
        return "bg-gradient-to-r from-gray-400/20 to-gray-500/10 border-gray-400/30";
      case 3:
        return "bg-gradient-to-r from-orange-400/20 to-orange-500/10 border-orange-400/30";
      default:
        return "";
    }
  };

  const leaderboard = leaderboardData?.leaderboard || [];
  const currentUserRank = leaderboard.findIndex((e) => e.id === salespersonId) + 1;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Leaderboard</h1>
          <p className="text-muted-foreground">
            Real-time team rankings and achievements
          </p>
        </div>
        {currentUserRank > 0 && (
          <Badge className="text-lg px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500">
            <Trophy className="h-5 w-5 mr-2" />
            Your Rank: #{currentUserRank}
          </Badge>
        )}
      </div>

      {/* Team Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Today's Leads</p>
                <p className="text-2xl font-bold">{statsData?.today.leads || 0}</p>
              </div>
              <Target className="h-6 w-6 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card className="border-orange-500/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Hot Leads Today</p>
                <p className="text-2xl font-bold text-orange-500">
                  {statsData?.today.hot_leads || 0}
                </p>
              </div>
              <Flame className="h-6 w-6 text-orange-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">This Week</p>
                <p className="text-2xl font-bold">{statsData?.this_week.leads || 0}</p>
              </div>
              <TrendingUp className="h-6 w-6 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Team</p>
                <p className="text-2xl font-bold">{leaderboard.length}</p>
              </div>
              <Users className="h-6 w-6 text-purple-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Leaderboard */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Trophy className="h-5 w-5 text-yellow-500" />
                Rankings
              </CardTitle>
              <Tabs value={period} onValueChange={(v) => setPeriod(v as typeof period)}>
                <TabsList>
                  <TabsTrigger value="TODAY">Today</TabsTrigger>
                  <TabsTrigger value="THIS_WEEK">Week</TabsTrigger>
                  <TabsTrigger value="THIS_MONTH">Month</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">Loading...</div>
            ) : leaderboard.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Trophy className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No activity yet for this period</p>
              </div>
            ) : (
              <div className="space-y-3">
                {leaderboard.map((entry, index) => {
                  const rank = index + 1;
                  const isCurrentUser = entry.id === salespersonId;

                  return (
                    <div
                      key={entry.id}
                      className={`flex items-center justify-between p-4 rounded-lg border transition-all
                        ${getRankBg(rank)}
                        ${isCurrentUser ? "ring-2 ring-primary" : ""}
                      `}
                    >
                      <div className="flex items-center gap-4">
                        <div
                          className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg
                            ${rank === 1 ? "bg-yellow-500 text-black" : ""}
                            ${rank === 2 ? "bg-gray-300 text-black" : ""}
                            ${rank === 3 ? "bg-orange-400 text-black" : ""}
                            ${rank > 3 ? "bg-muted" : ""}
                          `}
                        >
                          {rank <= 3 ? getRankIcon(rank) : rank}
                        </div>
                        <div>
                          <p className="font-medium">
                            {entry.first_name} {entry.last_name}
                            {isCurrentUser && (
                              <Badge variant="outline" className="ml-2 text-xs">
                                You
                              </Badge>
                            )}
                          </p>
                          <div className="flex items-center gap-3 text-sm text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Target className="h-3 w-3" />
                              {entry.leads_today} leads
                            </span>
                            <span className="flex items-center gap-1 text-orange-500">
                              <Flame className="h-3 w-3" />
                              {entry.hot_leads_today} hot
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold">{entry.points || 0}</p>
                        <p className="text-sm text-muted-foreground">points</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Achievements */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Award className="h-5 w-5 text-purple-500" />
              Your Achievements
            </CardTitle>
          </CardHeader>
          <CardContent>
            {achievementsData?.achievements && achievementsData.achievements.length > 0 ? (
              <div className="space-y-3">
                <div className="text-center p-4 rounded-lg bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/20">
                  <p className="text-3xl font-bold text-purple-500">
                    {achievementsData.total_points}
                  </p>
                  <p className="text-sm text-muted-foreground">Total Points</p>
                </div>
                {achievementsData.achievements.map((achievement) => (
                  <div
                    key={achievement.id}
                    className="flex items-center gap-3 p-3 rounded-lg bg-muted/50"
                  >
                    <div className="p-2 rounded-full bg-yellow-500/20">
                      <Star className="h-4 w-4 text-yellow-500" />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-sm">{achievement.achievement_type}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(achievement.earned_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Award className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No achievements yet</p>
                <p className="text-sm">Start canvassing to earn badges!</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Achievement Types */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Achievement Badges</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {[
              { name: "First Lead", icon: Star, description: "Capture your first lead" },
              { name: "Hot Streak", icon: Flame, description: "5 hot leads in a day" },
              { name: "Road Warrior", icon: Zap, description: "Complete 100 stops" },
              { name: "Top Performer", icon: Crown, description: "Rank #1 for a day" },
              { name: "Consistent", icon: TrendingUp, description: "Active 5 days straight" },
              { name: "Intel Master", icon: Trophy, description: "Log 10 competitors" },
            ].map((badge) => (
              <div
                key={badge.name}
                className="p-4 rounded-lg border text-center hover:border-primary/50 transition-colors"
              >
                <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-muted flex items-center justify-center">
                  <badge.icon className="h-6 w-6 text-muted-foreground" />
                </div>
                <p className="font-medium text-sm">{badge.name}</p>
                <p className="text-xs text-muted-foreground">{badge.description}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default LeaderboardPage;
