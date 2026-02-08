import { PageLayout } from '@/components/layout/PageLayout';
import { SkillGraph } from '@/components/charts/SkillGraph';
import { useGraphData } from '@/api/graph';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function GraphView() {
  const { data: graph, isLoading } = useGraphData();

  if (isLoading) {
    return (
      <PageLayout>
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
        </div>
      </PageLayout>
    );
  }

  if (!graph) {
    return (
      <PageLayout>
        <div className="text-slate-600">No graph data available.</div>
      </PageLayout>
    );
  }

  const linkTypes = Object.entries(graph.stats.link_type_distribution);

  return (
    <PageLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Skill Graph</h1>
          <p className="text-sm text-slate-500">
            Visual overview of skill relationships from the /api/graph endpoint.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Relationship Map</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[520px] rounded-lg border border-slate-200 bg-white">
              <SkillGraph nodes={graph.nodes} edges={graph.edges} />
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Graph Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-slate-600">
              <div className="flex justify-between">
                <span>Total nodes</span>
                <span className="font-semibold text-slate-900">{graph.stats.total_nodes}</span>
              </div>
              <div className="flex justify-between">
                <span>Total edges</span>
                <span className="font-semibold text-slate-900">{graph.stats.total_edges}</span>
              </div>
              <div className="flex justify-between">
                <span>Orphan nodes</span>
                <span className="font-semibold text-slate-900">{graph.stats.orphan_nodes}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Link Types</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-slate-600">
              {linkTypes.length === 0 ? (
                <div>No link types available.</div>
              ) : (
                linkTypes.map(([type, count]) => (
                  <div key={type} className="flex justify-between">
                    <span>{type}</span>
                    <span className="font-semibold text-slate-900">{count}</span>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </PageLayout>
  );
}
