import type { ChangedFile } from "@/lib/types";

export function ChangedFilesTable({ files }: { files: ChangedFile[] }) {
  if (files.length === 0) {
    return <p className="muted">No changed files recorded.</p>;
  }
  return (
    <table className="table">
      <thead>
        <tr>
          <th>File</th>
          <th>Status</th>
          <th className="num">+</th>
          <th className="num">−</th>
        </tr>
      </thead>
      <tbody>
        {files.map((f) => (
          <tr key={f.path}>
            <td className="mono">{f.path}</td>
            <td>{f.status}</td>
            <td className="num add">+{f.additions}</td>
            <td className="num del">−{f.deletions}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
