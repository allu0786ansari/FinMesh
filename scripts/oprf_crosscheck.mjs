import { derivePrivateKey, OPRFServer, OPRFClient, Oprf } from '@cloudflare/voprf-ts';
import { CryptoNoble } from '@cloudflare/voprf-ts/crypto-noble';
const hex = (u) => Buffer.from(u).toString('hex');
const suite = 'ristretto255-SHA512';
const cases = [
  { seed: 'a3'.repeat(32), info: Buffer.from('test key').toString('hex') },
  { seed: '00'.repeat(32), info: '' },
  { seed: '0f'.repeat(16) + 'f0'.repeat(16), info: Buffer.from('finmesh token service').toString('hex') },
];
const inputs = ['00', '5a'.repeat(17), Buffer.from('10:8000EBD30').toString('hex'), ''];
const out = [];
for (const c of cases) {
  const sk = await derivePrivateKey(Oprf.Mode.OPRF, suite, Buffer.from(c.seed, 'hex'), Buffer.from(c.info, 'hex'), CryptoNoble);
  const server = new OPRFServer(suite, sk, CryptoNoble);
  const evals = [];
  for (const i of inputs) {
    if (i === '') { evals.push(null); continue; }
    evals.push(hex(await server.evaluate(Buffer.from(i, 'hex'))));
  }
  // full protocol inside voprf-ts too
  const client = new OPRFClient(suite, CryptoNoble);
  const [fin, req] = await client.blind([Buffer.from('5a'.repeat(17), 'hex')]);
  const [y] = await client.finalize(fin, await server.blindEvaluate(req));
  out.push({ seed: c.seed, info: c.info, sk: hex(sk), inputs, evals, protocol_output: hex(y) });
}
console.log(JSON.stringify(out));
