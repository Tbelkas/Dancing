import { ApplicationConfig, ErrorHandler } from '@angular/core';
import { provideRouter, withInMemoryScrolling } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';
import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { ChunkErrorHandler } from './core/chunk-error.handler';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes, withInMemoryScrolling({
      // Back/forward returns to where you were (e.g. deep in the catalog);
      // normal navigations start at the top.
      scrollPositionRestoration: 'enabled',
      anchorScrolling: 'enabled'
    })),
    provideHttpClient(withInterceptors([authInterceptor])),
    provideAnimations(),
    { provide: ErrorHandler, useClass: ChunkErrorHandler }
  ]
};
