import Link from "next/link";

export default function NotFound() {
  return (
    <div className="prose py-10">
      <h1 className="text-3xl mb-3">No page here</h1>
      <p>
        The story is on the <Link className="underline" href="/">front page</Link>, and every other page is in the menu above.
      </p>
    </div>
  );
}
