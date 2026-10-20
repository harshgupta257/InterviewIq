import { Link } from "react-router-dom";
import { PublicLayout } from "@/components/layout";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <PublicLayout>
      <div className="container flex flex-col items-center justify-center gap-4 py-24 text-center">
        <p className="text-sm font-medium text-muted-foreground">404</p>
        <h1 className="display text-5xl">This page doesn't exist</h1>
        <p className="text-muted-foreground">The link may be broken or the page may have moved.</p>
        <Button asChild>
          <Link to="/">Go home</Link>
        </Button>
      </div>
    </PublicLayout>
  );
}
