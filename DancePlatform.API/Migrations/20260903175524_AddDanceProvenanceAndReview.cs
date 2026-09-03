using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddDanceProvenanceAndReview : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "OwnerUserId",
                table: "Dances",
                type: "integer",
                nullable: true);

            // "approved", NOT the empty string EF generates for a non-null string column: every
            // one of the 1051 dances already in the catalogue would otherwise land on a value no
            // query matches, and the browse page would go blank on deploy.
            //
            // The column default stays "approved" on purpose, unlike the Videos gate. Rows here
            // are inserted by the seeding scripts over psql, which are curation, not submissions;
            // it is the API that marks a non-admin's dance pending.
            migrationBuilder.AddColumn<string>(
                name: "ReviewState",
                table: "Dances",
                type: "text",
                nullable: false,
                defaultValue: "approved");

            migrationBuilder.CreateIndex(
                name: "IX_Dances_OwnerUserId",
                table: "Dances",
                column: "OwnerUserId");

            migrationBuilder.CreateIndex(
                name: "IX_Dances_ReviewState",
                table: "Dances",
                column: "ReviewState");

            migrationBuilder.AddForeignKey(
                name: "FK_Dances_Users_OwnerUserId",
                table: "Dances",
                column: "OwnerUserId",
                principalTable: "Users",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Dances_Users_OwnerUserId",
                table: "Dances");

            migrationBuilder.DropIndex(
                name: "IX_Dances_OwnerUserId",
                table: "Dances");

            migrationBuilder.DropIndex(
                name: "IX_Dances_ReviewState",
                table: "Dances");

            migrationBuilder.DropColumn(
                name: "OwnerUserId",
                table: "Dances");

            migrationBuilder.DropColumn(
                name: "ReviewState",
                table: "Dances");
        }
    }
}
