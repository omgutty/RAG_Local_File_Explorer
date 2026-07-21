package com.atb.pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

public class Mini {
    private WebDriver driver;

    public Mini(WebDriver driver) {
        this.driver = driver;
    }

    @Deprecated
    public void doLogin(String user, String pass) {
        driver.findElement(By.id("username")).sendKeys(user);
        driver.findElement(By.id("password")).sendKeys(pass);
        driver.findElement(By.id("login-btn")).click();
    }

    public String getErrorToast() {
        return driver.findElement(By.cssSelector("#error-toast")).getText();
    }
}
