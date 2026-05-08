import { Link } from "react-router-dom";

export function NotAuthorizedPage() {
  return (
    <div className="space-y-3 rounded-lg border border-red-200 bg-red-50 p-4">
      <h2 className="text-lg font-semibold text-red-800">Not Authorized</h2>
      <p className="text-sm text-slate-600">
        Your role or knowledge-base access level does not allow this action.
      </p>
      <Link className="text-sm font-medium text-blue-600 hover:underline" to="/">
        Back to dashboard
      </Link>
    </div>
  );
}
