import { loadProject, saveProject } from './io';
import fs from 'fs';

if (process.argv[2]) {
  const data = fs.readFileSync(process.argv[2], 'utf-8');
  const project = loadProject(data);
  console.log('Loaded project:', project.name);
  const out = saveProject(project);
  fs.writeFileSync('out.json', out);
}
