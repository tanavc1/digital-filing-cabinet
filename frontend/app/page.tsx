"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Loader2,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  FileText,
  BarChart3,
  Calendar,
  Clock,
  Users,
  Shield
} from "lucide-react";
import { useWorkspace } from "@/components/providers/workspace-provider";
import api from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function ProjectHome() {
  const { workspace } = useWorkspace();
  const router = useRouter();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        // Fetch stats from new endpoints
        // Assuming api.getProjectStats exists or we call fetch direct
        // Since I haven't added getProjectStats to frontend/lib/api.ts yet, I'll use fetch for demo speed
        // Or I should assume api.ts update is next.
        // I'll update api.ts next. For now, use fetch.
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/project/stats?workspace_id=${workspace.id}`);
        const data = await res.json();
        setStats(data);
      } catch (e) {
        console.error("Failed to load stats", e);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, [workspace.id]);

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold tracking-tight">Project Home</h1>
            <Badge variant="outline" className="text-indigo-600 border-indigo-200 bg-indigo-50">
              Assignment: Acquisition Diligence
            </Badge>
          </div>
          <p className="text-muted-foreground flex items-center gap-2">
            <Calendar className="w-4 h-4" />
            Deadline: <span className="font-semibold text-red-600">3 Days Remaining</span>
            <span className="text-gray-300 mx-2">|</span>
            <Users className="w-4 h-4" />
            Team: 3 Reviewers Active
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => router.push("/exports")}>
            <FileText className="w-4 h-4 mr-2" />
            View Deliverables
          </Button>
          <Button onClick={() => router.push("/review-queue")}>
            Continue Review
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>

      {/* Pipeline Progress */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm font-medium text-gray-600 mb-1">
          <span>Intake (Done)</span>
          <span>Review ({Math.round(stats.completion_percentage)}%)</span>
          <span>QA ({stats.qa_approved} Docs)</span>
          <span>Delivery</span>
        </div>
        <Progress value={stats.completion_percentage} className="h-3" />
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Docs Remaining</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.unreviewed}</div>
            <p className="text-xs text-muted-foreground">
              {stats.in_review} currently in progress
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Review Velocity</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.throughput_docs_per_hr}</div>
            <p className="text-xs text-muted-foreground">
              Docs per hour (Team avg)
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">QA Status</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.qa_approved}</div>
            <p className="text-xs text-muted-foreground pt-1">
              <span className="text-yellow-600 font-medium">{stats.qa_needed} Pending QA</span>
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Risks Flagged</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats.flagged}</div>
            <p className="text-xs text-muted-foreground">
              Requires Senior Review
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions / Activity */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2 space-y-6">
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Live stream of review actions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Mock activity feed */}
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-start gap-4 pb-4 border-b last:border-0 last:pb-0">
                    <div className="h-9 w-9 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-xs">
                      JD
                    </div>
                    <div>
                      <p className="text-sm font-medium">John Doe finished review of <span className="text-indigo-600">MSA_Acme_v2.pdf</span></p>
                      <p className="text-xs text-gray-500">2 minutes ago • 12 clauses extracted</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Delivery Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between items-center text-sm">
                <span className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-green-500" /> Clause Matrix</span>
                <Badge variant="secondary">Ready</Badge>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-green-500" /> Issues List</span>
                <Badge variant="secondary">Ready</Badge>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="flex items-center gap-2 text-gray-400"><Loader2 className="w-4 h-4" /> Evidence Pack</span>
                <Badge variant="outline">Processing</Badge>
              </div>
              <Button className="w-full mt-4" variant="secondary" onClick={() => router.push("/exports")}>
                Go to Exports
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
