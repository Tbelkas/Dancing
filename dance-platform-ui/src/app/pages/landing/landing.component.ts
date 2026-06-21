import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './landing.component.html',
  styleUrls: ['./landing.component.css']
})
export class LandingComponent implements OnInit {
  // A few real styles for the hero marquee — purely decorative.
  readonly marquee = ['Bachata', 'Salsa', 'Breakdance', 'Ballet', 'Hip-hop', 'Tango', 'Waacking', 'Popping', 'Contemporary', 'Jive', 'Flamenco', 'House'];
  // Equalizer bar heights (%) — static values, animated via CSS.
  readonly bars = [38, 64, 92, 52, 78, 44, 88, 60, 34, 72, 50, 84, 42, 68];

  constructor(private router: Router, public auth: AuthService) {}

  ngOnInit(): void {
    // Returning, signed-in dancers skip the pitch and go straight to their dances.
    if (this.auth.isAuthenticated()) {
      this.router.navigate(['/my-dances']);
    }
  }
}
