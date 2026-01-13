"use client";

import { Evidence, Doc } from "@/lib/types";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ExternalLink, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

interface EvidenceCardProps {
    evidence: Evidence;
    docTitle?: string;
}

export function EvidenceCard({ evidence, docTitle }: EvidenceCardProps) {
    return (
        <Card className="border-l-4 border-l-green-500 bg-green-50/20">
            <CardContent className="pt-4">
                <blockquote className="text-sm font-mono text-gray-700 border-l-2 pl-3 my-2 bg-white p-2 rounded border-gray-200">
                    "{evidence.quote}"
                </blockquote>
                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                    <CheckCircle2 className="w-3 h-3 text-green-600" />
                    <span>Verified Match</span>
                    <span className="text-gray-300">|</span>
                    <span>Confidence: {(evidence.confidence * 100).toFixed(0)}%</span>
                </div>
            </CardContent>
            <CardFooter className="bg-gray-50 p-3 flex justify-between items-center text-xs">
                <div className="truncate max-w-[200px] font-medium text-gray-700">
                    {docTitle || evidence.doc_id}
                </div>
                <Link
                    href={`/viewer/${evidence.doc_id}?highlight=${evidence.start_char},${evidence.end_char}`}
                >
                    <Button variant="outline" size="sm" className="h-7 text-xs gap-1">
                        View in Doc
                        <ExternalLink className="w-3 h-3" />
                    </Button>
                </Link>
            </CardFooter>
        </Card>
    );
}
