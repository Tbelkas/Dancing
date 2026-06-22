import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { appConfig } from './app/app.config';

bootstrapApplication(AppComponent, appConfig)
  // App booted cleanly — clear the chunk-reload guard so a future stale deploy
  // can recover too (see ChunkErrorHandler).
  .then(() => sessionStorage.removeItem('dp_chunk_reloaded'))
  .catch(err => console.error(err));
