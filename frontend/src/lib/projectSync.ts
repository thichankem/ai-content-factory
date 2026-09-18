/**
 * Keeping the project store and the query cache in step.
 *
 * Almost every mutation in the studio returns the updated :interface:`Project`,
 * and each of them used to repeat the same four lines of cache bookkeeping. That
 * duplication is the reason a screen could show a fresh project while another
 * screen kept the old one: one copy of the lines was updated, the other was not.
 *
 * :func:`syncProject` is now the only place that decision is made.
 */

import type { QueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/queryKeys";
import { useProjectStore } from "@/stores/useProjectStore";
import { Project } from "@/types/project";

/**
 * Write a server-returned project into the cache and the store.
 *
 * The selection is only re-pointed when the updated project *is* the selected
 * one (or when nothing is selected yet): a mutation fired for another project
 * must not yank the operator's current workspace out from under them.
 */
export function syncProject(queryClient: QueryClient, project: Project): void {
  queryClient.setQueryData<Project[]>(queryKeys.projects, (current) =>
    current?.some((item) => item.id === project.id)
      ? current.map((item) => (item.id === project.id ? project : item))
      : [...(current ?? []), project]
  );
  queryClient.setQueryData(queryKeys.project(project.id), project);

  const { currentProject, setCurrentProject } = useProjectStore.getState();
  if (!currentProject || currentProject.id === project.id) {
    setCurrentProject(project);
  }
}

/**
 * Invalidate everything derived from a project's timeline.
 *
 * Scene edits change the render plan and the timeline report as a side effect, so
 * those queries are dropped rather than patched — the backend recomputes them and
 * duplicating that logic in the client is how the two drift apart.
 */
export function invalidateTimeline(
  queryClient: QueryClient,
  projectId: string
): void {
  void queryClient.invalidateQueries({ queryKey: queryKeys.videoProject(projectId) });
  void queryClient.invalidateQueries({ queryKey: queryKeys.timelineReport(projectId) });
  void queryClient.invalidateQueries({ queryKey: queryKeys.renderPlan(projectId) });
}