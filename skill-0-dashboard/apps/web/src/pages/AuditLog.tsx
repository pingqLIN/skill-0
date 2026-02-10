<<<<<<< Updated upstream
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageLayout } from '@/components/layout/PageLayout';
import { useAuditLog } from '@/api/audit';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ChevronLeft, ChevronRight, Search, History } from 'lucide-react';

const eventTypeColors: Record<string, string> = {
  create: 'bg-green-100 text-green-800',
  update: 'bg-blue-100 text-blue-800',
  approve: 'bg-emerald-100 text-emerald-800',
  reject: 'bg-red-100 text-red-800',
  scan: 'bg-purple-100 text-purple-800',
  test: 'bg-amber-100 text-amber-800',
  block: 'bg-gray-100 text-gray-800',
  import: 'bg-indigo-100 text-indigo-800',
};

export function AuditLog() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [eventType, setEventType] = useState('');
  const [skillIdFilter, setSkillIdFilter] = useState('');

  const { data, isLoading } = useAuditLog({
    page,
    page_size: 50,
    event_type: eventType || undefined,
    skill_id: skillIdFilter || undefined,
  });

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

  return (
    <PageLayout>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <History className="h-6 w-6" />
          Audit Log
        </h1>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Filter by Skill ID..."
                  value={skillIdFilter}
                  onChange={(e) => { setSkillIdFilter(e.target.value); setPage(1); }}
                  className="pl-10"
                />
              </div>
            </div>
            <select
              value={eventType}
              onChange={(e) => { setEventType(e.target.value); setPage(1); }}
              className="border rounded-md px-3 py-2"
            >
              <option value="">All Events</option>
              <option value="create">Create</option>
              <option value="update">Update</option>
              <option value="approve">Approve</option>
              <option value="reject">Reject</option>
              <option value="scan">Scan</option>
              <option value="test">Test</option>
              <option value="block">Block</option>
              <option value="import">Import</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            {data ? `${data.total} events` : 'Loading...'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
            </div>
          ) : data?.items.length === 0 ? (
            <p className="text-center py-8 text-muted-foreground">No audit events found</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Event</TableHead>
                  <TableHead>Skill</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((event) => (
                  <TableRow key={event.event_id}>
                    <TableCell className="whitespace-nowrap text-sm">
                      {new Date(event.timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Badge className={eventTypeColors[event.event_type] || 'bg-gray-100 text-gray-800'}>
                        {event.event_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {event.skill_name ? (
                        <button
                          onClick={() => event.skill_id && navigate(`/skills/${event.skill_id}`)}
                          className="text-blue-600 hover:text-blue-800 hover:underline text-left"
                        >
                          {event.skill_name}
                        </button>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>{event.actor}</TableCell>
                    <TableCell>
                      {event.details && typeof event.details === 'object' ? (
                        <details className="cursor-pointer">
                          <summary className="text-sm text-muted-foreground hover:text-foreground">
                            {Object.keys(event.details).length} field(s)
                          </summary>
                          <pre className="text-xs bg-slate-50 p-2 rounded mt-1 max-w-[300px] overflow-auto">
                            {JSON.stringify(event.details, null, 2)}
                          </pre>
                        </details>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Pagination */}
          {data && totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <p className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </PageLayout>
  );
}
=======
import { PageLayout } from '@/components/layout/PageLayout';

export function AuditLog() {
  return (
    <PageLayout>
      <h1 className="text-2xl font-bold mb-6">Audit Log</h1>
      <div className="p-4 bg-white rounded-lg border border-slate-200">
        <p className="text-slate-500">Audit log coming soon...</p>
      </div>
    </PageLayout>
  );
}
>>>>>>> Stashed changes
