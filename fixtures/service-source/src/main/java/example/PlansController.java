package example;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/mobile2api/v1/plans")
public class PlansController {
    @GetMapping
    public Object getPlans() { return null; }

    @GetMapping("/{planId}")
    public Object getPlanById(@PathVariable String planId) { return null; }
}
