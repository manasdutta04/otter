import { redirect } from "next/navigation";

/** Product UI only — marketing lives on apps/site (Vercel). */
export default function RootRedirect() {
  redirect("/app");
}
