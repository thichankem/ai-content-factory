/**
 * QA hooks: platform, brand and copyright verification.
 *
 * These are the checks that run *before* a gate. They never approve anything —
 * the two human gates remain the only paths that move a project forward, and the
 * backend refuses an out-of-order approval.
 */

import { useMutation } from "@tanstack/react-query";

import { qaApi } from "@/lib/api";
import {
  BrandCheckRequest,
  CopyrightCheckRequest,
  PlatformCheckRequest,
} from "@/types/qa";

export function useQA() {
  const platformQAMutation = useMutation({
    mutationFn: (req: PlatformCheckRequest) => qaApi.platformVerdict(req),
  });

  const brandQAMutation = useMutation({
    mutationFn: (req: BrandCheckRequest) => qaApi.brandVerdict(req),
  });

  const copyrightMutation = useMutation({
    mutationFn: (req: CopyrightCheckRequest) => qaApi.copyrightVerdict(req),
  });

  const simplifySubtitlesMutation = useMutation({
    mutationFn: (captions: string[]) =>
      qaApi.simplifySubtitles({ captions, level: "basic" }),
  });

  return {
    platformQAMutation,
    brandQAMutation,
    copyrightMutation,
    simplifySubtitlesMutation,
  };
}