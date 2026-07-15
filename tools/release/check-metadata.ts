import { validateReleaseMetadata } from "./metadata-lib";

const metadata = validateReleaseMetadata();
console.log(`release metadata is synchronized for ${metadata.release.tag}`);
