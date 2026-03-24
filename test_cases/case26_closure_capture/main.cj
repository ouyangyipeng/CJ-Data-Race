// case26: 闭包捕获变量竞争测试
// 测试闭包中捕获变量可能导致的数据竞争

main() {
    var counter: Int64 = 0
    
    // 闭包捕获counter变量
    let increment = { =>
        counter = counter + 1  // 写操作
    }
    
    let decrement = { =>
        counter = counter - 1  // 写操作
    }
    
    // 多个线程执行闭包
    spawn increment
    spawn decrement
    
    // 主线程也访问
    counter = 10  // 写操作
}