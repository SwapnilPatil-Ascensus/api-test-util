package example;

public class PlansRequestTest {
  void getPlans() {
    given().header("Authorization", "Bearer {{accessToken}}").get("/mobile2api/v1/plans");
  }

  void getPlan() {
    given().get("/mobile2api/v1/plans/{{planId}}");
  }
}
