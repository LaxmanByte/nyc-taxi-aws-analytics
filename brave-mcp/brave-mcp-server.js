import express from 'express';
import 'dotenv/config';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { z } from 'zod';

const BRAVE_API_KEY = process.env.BRAVE_API_KEY;
if (!BRAVE_API_KEY) { console.error('BRAVE_API_KEY required'); process.exit(1); }

function buildServer() {
  const server = new McpServer({ name: 'brave-search', version: '1.0.0' });
  server.tool(
    'brave_search',
    'Search the web via Brave Search API',
    { query: z.string(), count: z.number().min(1).max(20).optional() },
    async ({ query, count = 10 }) => {
      const url = new URL('https://api.search.brave.com/res/v1/web/search');
      url.searchParams.set('q', query);
      url.searchParams.set('count', String(count));
      const r = await fetch(url, {
        headers: { Accept: 'application/json', 'X-Subscription-Token': BRAVE_API_KEY }
      });
      if (!r.ok) throw new Error(`Brave API ${r.status}`);
      const data = await r.json();
      const results = (data.web?.results ?? []).map(x => ({
        title: x.title, url: x.url, description: x.description
      }));
      return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
    }
  );
  return server;
}

const app = express();
app.use(express.json());

app.post('/mcp', async (req, res) => {
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
  res.on('close', () => transport.close());
  const server = buildServer();
  await server.connect(transport);
  await transport.handleRequest(req, res, req.body);
});
app.get('/mcp', (_, res) => res.status(405).end());
app.delete('/mcp', (_, res) => res.status(405).end());

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`MCP server on :${PORT}/mcp`));
