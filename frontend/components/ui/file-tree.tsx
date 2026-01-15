
import { useState, useMemo } from "react";
import { Doc } from "@/lib/types";
import {
    Folder,
    FileText,
    ChevronRight,
    ChevronDown,
    File as FileIcon,
    AlertCircle,
    CheckCircle
} from "lucide-react";
import { cn } from "@/lib/utils";

interface FileTreeProps {
    docs: Doc[];
    onSelectDoc?: (doc: Doc) => void;
    selectedDocId?: string | null;
}

interface TreeNode {
    name: string;
    path: string;
    type: "file" | "folder";
    children: Record<string, TreeNode>;
    doc?: Doc;
}

const buildTree = (docs: Doc[]) => {
    const root: TreeNode = { name: "root", path: "/", type: "folder", children: {} };

    docs.forEach(doc => {
        // Normalize path
        const folderPath = doc.folder_path || "/";
        const parts = folderPath.split("/").filter(Boolean);

        let current = root;

        // Traverse folders
        parts.forEach((part, idx) => {
            const currentPath = "/" + parts.slice(0, idx + 1).join("/");
            if (!current.children[part]) {
                current.children[part] = {
                    name: part,
                    path: currentPath,
                    type: "folder",
                    children: {}
                };
            }
            current = current.children[part];
        });

        // Add file
        // Use title or fallback to doc_id if title is empty
        const fileName = doc.title || doc.doc_id.slice(0, 8);
        current.children[doc.doc_id] = {
            name: fileName,
            path: (folderPath === "/" ? "" : folderPath) + "/" + fileName,
            type: "file",
            children: {},
            doc: doc
        };
    });

    return root;
};

const FileIconByType = ({ doc }: { doc: Doc }) => {
    // Determine icon based on doc_type or filename
    if (doc.doc_type === "NDA") return <FileText className="w-4 h-4 text-purple-500" />;
    if (doc.doc_type?.includes("Lease")) return <FileText className="w-4 h-4 text-orange-500" />;
    return <FileText className="w-4 h-4 text-gray-500" />;
};

const RiskBadge = ({ level }: { level?: string }) => {
    if (!level || level === "Unknown") return null;
    if (level === "High") return <span className="ml-2 w-2 h-2 rounded-full bg-red-500" title="High Risk" />;
    if (level === "Medium") return <span className="ml-2 w-2 h-2 rounded-full bg-yellow-500" title="Medium Risk" />;
    if (level === "Clean" || level === "Low") return <span className="ml-2 w-2 h-2 rounded-full bg-green-500" title="Clean" />;
    return null;
};

const TreeNodeView = ({ node, level, onSelect, selectedId }: { node: TreeNode, level: number, onSelect: any, selectedId?: string | null }) => {
    const [isOpen, setIsOpen] = useState(level < 1); // Expand top level by default
    const hasChildren = Object.keys(node.children).length > 0;

    if (node.type === "file" && node.doc) {
        return (
            <div
                className={cn(
                    "flex items-center py-1 px-2 hover:bg-gray-100 cursor-pointer rounded text-sm transition-colors",
                    selectedId === node.doc.doc_id && "bg-blue-50 text-blue-700"
                )}
                style={{ paddingLeft: `${level * 12 + 4}px` }}
                onClick={() => onSelect(node.doc)}
            >
                <FileIconByType doc={node.doc} />
                <span className="ml-2 truncate flex-1">{node.name}</span>
                <span className="text-[10px] text-gray-400 ml-2 border px-1 rounded bg-white">
                    {node.doc.doc_type || "??"}
                </span>
                <RiskBadge level={node.doc.risk_level} />
            </div>
        );
    }

    return (
        <div>
            <div
                className="flex items-center py-1 px-2 hover:bg-gray-50 cursor-pointer text-sm font-medium text-gray-700 select-none"
                style={{ paddingLeft: `${level * 12}px` }}
                onClick={() => setIsOpen(!isOpen)}
            >
                {hasChildren ? (
                    isOpen ? <ChevronDown className="w-4 h-4 text-gray-400 mr-1" /> : <ChevronRight className="w-4 h-4 text-gray-400 mr-1" />
                ) : <span className="w-5" />}

                <Folder className="w-4 h-4 text-blue-300 mr-2 fill-blue-50" />
                <span className="truncate">{node.name === "root" ? "Data Room" : node.name}</span>
            </div>
            {isOpen && (
                <div>
                    {Object.values(node.children)
                        .sort((a, b) => {
                            // Folders first, then files
                            if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
                            return a.name.localeCompare(b.name);
                        })
                        .map((child) => (
                            <TreeNodeView
                                key={child.doc?.doc_id || child.path}
                                node={child}
                                level={level + 1}
                                onSelect={onSelect}
                                selectedId={selectedId}
                            />
                        ))}
                </div>
            )}
        </div>
    );
};

export function FileTree({ docs, onSelectDoc, selectedDocId }: FileTreeProps) {
    const root = useMemo(() => buildTree(docs), [docs]);

    if (!docs || docs.length === 0) {
        return <div className="text-gray-400 text-sm p-4 text-center">Data Deal Room is empty.</div>;
    }

    return (
        <div className="overflow-y-auto h-full pb-4">
            {/* Render Children of Root directly so we don't see a "root" folder if we prefer flat top level */}
            {/* Actually, mirroring VDR usually implies a root, let's just render the root contents */}
            {Object.values(root.children)
                .sort((a, b) => {
                    if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
                    return a.name.localeCompare(b.name);
                })
                .map((child) => (
                    <TreeNodeView
                        key={child.doc?.doc_id || child.path}
                        node={child}
                        level={0}
                        onSelect={onSelectDoc}
                        selectedId={selectedDocId}
                    />
                ))}
        </div>
    );
}
