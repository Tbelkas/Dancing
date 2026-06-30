using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddVideoOwner : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "OwnerUserId",
                table: "Videos",
                type: "integer",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_Videos_OwnerUserId",
                table: "Videos",
                column: "OwnerUserId");

            migrationBuilder.AddForeignKey(
                name: "FK_Videos_Users_OwnerUserId",
                table: "Videos",
                column: "OwnerUserId",
                principalTable: "Users",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Videos_Users_OwnerUserId",
                table: "Videos");

            migrationBuilder.DropIndex(
                name: "IX_Videos_OwnerUserId",
                table: "Videos");

            migrationBuilder.DropColumn(
                name: "OwnerUserId",
                table: "Videos");
        }
    }
}
