"use client";

import { Doc } from "@/lib/types";
import { deleteDoc } from "@/lib/api";
import { Trash2, FileText, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { useWorkspace } from "@/components/providers/workspace-provider";
import Link from "next/link";

interface DocTableProps {
    docs: Doc[];
    onDelete: () => void;
}

export function DocTable({ docs, onDelete }: DocTableProps) {
    const { workspace, refreshDocs } = useWorkspace();

    const handleDelete = async (docId: string) => {
        if (confirm("Are you sure you want to delete this document?")) {
            await deleteDoc(docId, workspace.id);
            onDelete();
            // Update global count in sidebar
            refreshDocs();
        }
    };

    if (docs.length === 0) {
        return (
            <div className="text-center py-12 text-gray-500 border rounded-lg bg-gray-50 border-dashed">
                No documents in this workspace yet.
            </div>
        );
    }

    return (
        <div className="border rounded-md">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>Document</TableHead>
                        <TableHead>Source</TableHead>
                        <TableHead>Modified</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {docs.map((doc) => (
                        <TableRow key={doc.doc_id}>
                            <TableCell className="font-medium">
                                <div className="flex items-center gap-2">
                                    <FileText className="w-4 h-4 text-blue-500" />
                                    {doc.title}
                                </div>
                            </TableCell>
                            <TableCell className="text-gray-500">{doc.source}</TableCell>
                            <TableCell className="text-gray-500">
                                {new Date(doc.modified_at * 1000).toLocaleDateString()}
                            </TableCell>
                            <TableCell className="text-right">
                                <div className="flex justify-end gap-2">
                                    <Link href={`/viewer/${doc.doc_id}`} className="cursor-pointer">
                                        <Button variant="ghost" size="icon" className="cursor-pointer hover:bg-gray-100">
                                            <Eye className="w-4 h-4 text-gray-500" />
                                        </Button>
                                    </Link>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="cursor-pointer hover:bg-red-50"
                                        onClick={() => handleDelete(doc.doc_id)}
                                    >
                                        <Trash2 className="w-4 h-4 text-red-500" />
                                    </Button>
                                </div>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}
