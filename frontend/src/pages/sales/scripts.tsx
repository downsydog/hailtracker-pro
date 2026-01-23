/**
 * Smart Scripts Page
 * Sales scripts and objection handling guides
 */

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  MessageSquare,
  Copy,
  Check,
  DollarSign,
  Clock,
  Shield,
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
  Lightbulb,
  Target,
  Phone,
} from "lucide-react";
import { getScript, logObjection } from "@/api/elite-sales";

const SCRIPT_CATEGORIES = [
  {
    id: "DOOR_APPROACH",
    name: "Door Approach",
    icon: Target,
    description: "Opening scripts for initial contact",
  },
  {
    id: "OBJECTION_PRICE",
    name: "Price Objection",
    icon: DollarSign,
    description: "Handling price concerns",
  },
  {
    id: "OBJECTION_TIME",
    name: "Time Objection",
    icon: Clock,
    description: "When they say 'not now'",
  },
  {
    id: "OBJECTION_INSURANCE",
    name: "Insurance Objection",
    icon: Shield,
    description: "Insurance-related concerns",
  },
  {
    id: "CLOSE_APPOINTMENT",
    name: "Closing",
    icon: Phone,
    description: "Scripts to close the appointment",
  },
];

export function ScriptsPage() {
  const salespersonId = 1; // TODO: Get from auth context
  const [selectedCategory, setSelectedCategory] = useState("DOOR_APPROACH");
  const [copiedScript, setCopiedScript] = useState<string | null>(null);
  const [logOutcomeOpen, setLogOutcomeOpen] = useState(false);
  const [selectedOutcome, setSelectedOutcome] = useState<string | null>(null);

  // Fetch script for selected category
  const { data: scriptData, isLoading } = useQuery({
    queryKey: ["script", selectedCategory],
    queryFn: () => getScript(selectedCategory),
  });

  // Log objection mutation
  const logObjectionMutation = useMutation({
    mutationFn: (outcome: string) =>
      logObjection({
        salesperson_id: salespersonId,
        objection_type: selectedCategory,
        response_used: "Standard script",
        outcome,
      }),
    onSuccess: () => {
      setLogOutcomeOpen(false);
      setSelectedOutcome(null);
    },
  });

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedScript(id);
    setTimeout(() => setCopiedScript(null), 2000);
  };

  const currentCategory = SCRIPT_CATEGORIES.find((c) => c.id === selectedCategory);
  const script = scriptData?.script;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Smart Scripts</h1>
          <p className="text-muted-foreground">
            Sales scripts and objection handling guides
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Category Selection */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Categories</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y">
              {SCRIPT_CATEGORIES.map((category) => {
                const Icon = category.icon;
                const isSelected = selectedCategory === category.id;

                return (
                  <button
                    key={category.id}
                    onClick={() => setSelectedCategory(category.id)}
                    className={`w-full p-4 text-left transition-colors flex items-start gap-3
                      ${isSelected ? "bg-primary/10 border-l-4 border-primary" : "hover:bg-muted/50"}
                    `}
                  >
                    <Icon
                      className={`h-5 w-5 mt-0.5 ${
                        isSelected ? "text-primary" : "text-muted-foreground"
                      }`}
                    />
                    <div>
                      <p className={`font-medium ${isSelected ? "text-primary" : ""}`}>
                        {category.name}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {category.description}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Script Content */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                {currentCategory && <currentCategory.icon className="h-5 w-5" />}
                {currentCategory?.name}
              </CardTitle>
              <Button variant="outline" onClick={() => setLogOutcomeOpen(true)}>
                <MessageSquare className="h-4 w-4 mr-2" />
                Log Outcome
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">Loading script...</div>
            ) : script ? (
              <>
                {/* Opening */}
                {script.opening && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-medium">Opening</h3>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(script.opening!, "opening")}
                      >
                        {copiedScript === "opening" ? (
                          <Check className="h-4 w-4 text-green-500" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                    <div className="p-4 rounded-lg bg-muted/50 border">
                      <p className="whitespace-pre-wrap">{script.opening}</p>
                    </div>
                  </div>
                )}

                {/* Response */}
                {script.response && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-medium">Response</h3>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(script.response!, "response")}
                      >
                        {copiedScript === "response" ? (
                          <Check className="h-4 w-4 text-green-500" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                    <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                      <p className="whitespace-pre-wrap">{script.response}</p>
                    </div>
                  </div>
                )}

                {/* Key Points */}
                {script.key_points && script.key_points.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="font-medium">Key Points</h3>
                    <div className="grid gap-2">
                      {script.key_points.map((point, index) => (
                        <div
                          key={index}
                          className="flex items-start gap-2 p-3 rounded-lg bg-muted/50"
                        >
                          <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold">
                            {index + 1}
                          </div>
                          <p className="flex-1">{point}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Tips */}
                {script.tips && script.tips.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="font-medium flex items-center gap-2">
                      <Lightbulb className="h-4 w-4 text-yellow-500" />
                      Pro Tips
                    </h3>
                    <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                      <ul className="space-y-2">
                        {script.tips.map((tip, index) => (
                          <li key={index} className="flex items-start gap-2">
                            <Check className="h-4 w-4 text-yellow-500 mt-0.5" />
                            <span>{tip}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <MessageSquare className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No script available for this category</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Reference Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-green-500" />
              Price Objection Quick Response
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              "I completely understand. Many of my customers felt the same way initially. However,
              they found that getting professional PDR repair actually saved them money compared to
              body shop work, and it maintains their vehicle's original paint and value."
            </p>
            <Button
              variant="ghost"
              size="sm"
              className="mt-2"
              onClick={() =>
                copyToClipboard(
                  "I completely understand. Many of my customers felt the same way initially. However, they found that getting professional PDR repair actually saved them money compared to body shop work, and it maintains their vehicle's original paint and value.",
                  "price-quick"
                )
              }
            >
              {copiedScript === "price-quick" ? (
                <>
                  <Check className="h-4 w-4 mr-2 text-green-500" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4 mr-2" />
                  Copy
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="h-4 w-4 text-blue-500" />
              Time Objection Quick Response
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              "I understand you're busy. That's exactly why we offer flexible scheduling - we can
              work around your schedule. Most repairs only take a few hours, and we can come to your
              home or office. When would be a convenient time for a free estimate?"
            </p>
            <Button
              variant="ghost"
              size="sm"
              className="mt-2"
              onClick={() =>
                copyToClipboard(
                  "I understand you're busy. That's exactly why we offer flexible scheduling - we can work around your schedule. Most repairs only take a few hours, and we can come to your home or office. When would be a convenient time for a free estimate?",
                  "time-quick"
                )
              }
            >
              {copiedScript === "time-quick" ? (
                <>
                  <Check className="h-4 w-4 mr-2 text-green-500" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4 mr-2" />
                  Copy
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Shield className="h-4 w-4 text-purple-500" />
              Insurance Quick Response
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              "Great question! Most comprehensive insurance policies cover hail damage with no impact
              to your rates since it's an act of nature. We work directly with your insurance
              company to make the process easy. Would you like me to help you check your coverage?"
            </p>
            <Button
              variant="ghost"
              size="sm"
              className="mt-2"
              onClick={() =>
                copyToClipboard(
                  "Great question! Most comprehensive insurance policies cover hail damage with no impact to your rates since it's an act of nature. We work directly with your insurance company to make the process easy. Would you like me to help you check your coverage?",
                  "insurance-quick"
                )
              }
            >
              {copiedScript === "insurance-quick" ? (
                <>
                  <Check className="h-4 w-4 mr-2 text-green-500" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4 mr-2" />
                  Copy
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Log Outcome Dialog */}
      <Dialog open={logOutcomeOpen} onOpenChange={setLogOutcomeOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Log Objection Outcome</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <p className="text-muted-foreground">
              How did the conversation go after using the script?
            </p>
            <div className="grid grid-cols-3 gap-4">
              <Button
                variant={selectedOutcome === "CONVERTED" ? "default" : "outline"}
                className={`h-24 flex-col gap-2 ${
                  selectedOutcome === "CONVERTED" ? "bg-green-500 hover:bg-green-600" : ""
                }`}
                onClick={() => setSelectedOutcome("CONVERTED")}
              >
                <ThumbsUp className="h-6 w-6" />
                Converted
              </Button>
              <Button
                variant={selectedOutcome === "FOLLOW_UP" ? "default" : "outline"}
                className={`h-24 flex-col gap-2 ${
                  selectedOutcome === "FOLLOW_UP" ? "bg-yellow-500 hover:bg-yellow-600 text-black" : ""
                }`}
                onClick={() => setSelectedOutcome("FOLLOW_UP")}
              >
                <RefreshCw className="h-6 w-6" />
                Follow Up
              </Button>
              <Button
                variant={selectedOutcome === "LOST" ? "default" : "outline"}
                className={`h-24 flex-col gap-2 ${
                  selectedOutcome === "LOST" ? "bg-red-500 hover:bg-red-600" : ""
                }`}
                onClick={() => setSelectedOutcome("LOST")}
              >
                <ThumbsDown className="h-6 w-6" />
                Lost
              </Button>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLogOutcomeOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => selectedOutcome && logObjectionMutation.mutate(selectedOutcome)}
              disabled={!selectedOutcome || logObjectionMutation.isPending}
            >
              {logObjectionMutation.isPending ? "Saving..." : "Log Outcome"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default ScriptsPage;
