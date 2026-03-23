// 测试用例8: 嵌套spawn
// spawn内部再创建线程，检测嵌套线程间的竞争

main() {
    var counter: Int64 = 0
    
    // 外层spawn
    spawn {
        counter = counter + 1  // 写操作
        
        // 内层spawn
        spawn {
            counter = counter + 1  // 写操作，与外层竞争
        }
    }
    
    // 另一个外层spawn
    spawn {
        counter = counter + 1  // 写操作，与其他线程竞争
    }
    
    println(counter)
}