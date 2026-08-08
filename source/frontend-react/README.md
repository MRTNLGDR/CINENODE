# React/Vibe integration shell

This strict TypeScript shell is the controlled integration point for the complete upstream
`SamurAIGPT/Vibe-Workflow/packages/workflow-builder` checkout. The validated distribution
uses the zero-dependency frontend in `source/frontend` so it can start without Node.js.
After `scripts/bootstrap-opensources.*` has cloned the pinned upstream, run `npm install &&
npm run build` here to build the React/Vibe variant. It consumes the same FastAPI contract.
