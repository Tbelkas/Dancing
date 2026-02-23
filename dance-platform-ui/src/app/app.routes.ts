import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'dances', pathMatch: 'full' },
  { path: 'login', loadComponent: () => import('./pages/login/login.component').then(m => m.LoginComponent) },
  { path: 'dances', loadComponent: () => import('./pages/dances/dances.component').then(m => m.DancesComponent) },
  { path: 'dances/:id', loadComponent: () => import('./pages/dance-detail/dance-detail.component').then(m => m.DanceDetailComponent) },
  { path: 'profile', loadComponent: () => import('./pages/profile/profile.component').then(m => m.ProfileComponent), canActivate: [authGuard] },
  { path: '**', redirectTo: 'dances' }
];
