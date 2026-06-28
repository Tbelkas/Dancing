using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class SlugIndexNonUnique : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "IX_Dances_Slug",
                table: "Dances");

            migrationBuilder.CreateIndex(
                name: "IX_Dances_Slug",
                table: "Dances",
                column: "Slug");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "IX_Dances_Slug",
                table: "Dances");

            migrationBuilder.CreateIndex(
                name: "IX_Dances_Slug",
                table: "Dances",
                column: "Slug",
                unique: true);
        }
    }
}
