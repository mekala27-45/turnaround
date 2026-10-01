"use client";

import { useEffect } from "react";

import { markReady } from "@/lib/ready";

/** On a page that runs no query, ready as soon as it has mounted. */
export function MarkReady() {
  useEffect(() => {
    markReady();
  }, []);
  return null;
}
