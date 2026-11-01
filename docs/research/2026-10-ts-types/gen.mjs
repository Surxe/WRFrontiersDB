import {compile} from 'json-schema-to-typescript'; import fs from 'fs';
const [,, file, ap] = process.argv;
const s = JSON.parse(fs.readFileSync(file));
console.log(await compile(s, 'WrfModels', {additionalProperties: ap === 'true', bannerComment: '', unreachableDefinitions: true}));
