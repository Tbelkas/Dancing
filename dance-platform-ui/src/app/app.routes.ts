import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { adminGuard } from './core/guards/admin.guard';

export const routes: Routes = [
  { path: '', title: 'Dance Platform · Learn any dance, one loop at a time', loadComponent: () => import('./pages/landing/landing.component').then(m => m.LandingComponent) },
  { path: 'login', title: 'Sign in · Dance Platform', loadComponent: () => import('./pages/login/login.component').then(m => m.LoginComponent) },
  { path: 'register', title: 'Create account · Dance Platform', loadComponent: () => import('./pages/login/login.component').then(m => m.LoginComponent) },
  { path: 'dances', title: 'Browse Dances · Dance Platform', loadComponent: () => import('./pages/dances/dances.component').then(m => m.DancesComponent) },
  { path: 'dances/:style/:slug', loadComponent: () => import('./pages/dance-detail/dance-detail.component').then(m => m.DanceDetailComponent) },
  { path: 'dances/:slug', loadComponent: () => import('./pages/dance-detail/dance-detail.component').then(m => m.DanceDetailComponent) },
  { path: 'profile', title: 'My Profile · Dance Platform', loadComponent: () => import('./pages/profile/profile.component').then(m => m.ProfileComponent), canActivate: [authGuard] },
  { path: 'my-dances', title: 'My Dances · Dance Platform', loadComponent: () => import('./pages/my-dances/my-dances.component').then(m => m.MyDancesComponent), canActivate: [authGuard] },
  { path: 'practice', title: 'Practice Log · Dance Platform', loadComponent: () => import('./pages/practice/practice.component').then(m => m.PracticeComponent), canActivate: [authGuard] },
  { path: 'admin/add-video', title: 'Add Video · Dance Platform', loadComponent: () => import('./pages/admin-add-video/admin-add-video.component').then(m => m.AdminAddVideoComponent), canActivate: [adminGuard] },
  { path: 'users/:username', loadComponent: () => import('./pages/user-profile/user-profile.component').then(m => m.UserProfileComponent) },
  { path: '**', title: 'Page not found · Dance Platform', loadComponent: () => import('./pages/not-found/not-found.component').then(m => m.NotFoundComponent) }
];
